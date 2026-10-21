"""OpenCode writes the proof in a Sandbox; a Sidecar with no network verifies it."""

import json
import time

import modal

from support.model import load_endpoint
from verify import ROOT, image

OPENCODE = "1.19.3"
PROMPT = """Implement the Maximum trait from /contract/spec.rs in /work/candidate.rs.
Check it with `curl -s --data-binary @/work/candidate.rs http://verifier:8080`, which runs
Verus against the contract and prints the errors. Repeat until it reports 0 errors.
Do not use assume, admit, external_body, or other verification bypasses."""

agent_image = (
    modal.Image.debian_slim()
    .apt_install("curl")
    .run_commands(f"curl -fsSL https://opencode.ai/install | bash -s -- --version {OPENCODE}")
    .add_local_file(ROOT / "contract/spec.rs", "/contract/spec.rs", copy=True)
    .add_local_file(ROOT / "contract/candidate.rs", "/work/candidate.rs", copy=True)
    .env({"PATH": "/root/.opencode/bin:/usr/bin:/bin", "OPENCODE_DISABLE_MODELS_FETCH": "1"})
)
# The verifier checks against its own copy of the contract, which the agent cannot reach.
verifier_image = (
    image.apt_install("python3")
    .add_local_file(ROOT / "contract/main.rs", "/contract/main.rs", copy=True)
    .add_local_file(ROOT / "contract/spec.rs", "/contract/spec.rs", copy=True)
    .add_local_file(ROOT / "support/verifier.py", "/verifier.py", copy=True)
)
app = modal.App("verus-agent")


@app.local_entrypoint()
def main():
    endpoint = load_endpoint()
    options = {"baseURL": endpoint.url, "apiKey": endpoint.key}
    config = {"provider": {"modal": {"options": options, "models": {endpoint.model: {}}}}}
    verifier_image.build(app)  # Sidecar images must be built before the Sidecar is created.
    sb = modal.Sandbox.create(
        app=app,
        image=agent_image,
        workdir="/work",
        timeout=20 * 60,
        outbound_domain_allowlist=[endpoint.host],  # The agent reaches the model only.
    )
    try:
        verifier = sb._experimental_sidecars.create(
            "python3",
            "/verifier.py",
            name="verifier",
            image=verifier_image,
            outbound_cidr_allowlist=[],  # The verifier reaches nothing.
        )
        sb.filesystem.write_text(json.dumps(config), "/root/.config/opencode/opencode.json")
        start = time.monotonic()
        agent = sb.exec(
            "sh",
            "-c",
            'opencode run --auto -m "$1" "$2" < /dev/null 2>&1',  # OpenCode waits for stdin EOF.
            "agent",
            f"modal/{endpoint.model}",
            PROMPT,
            timeout=15 * 60,
        )
        for line in agent.stdout:
            print(line, end="")
        agent.wait()

        # The verdict comes from the driver's own call to the verifier, not from the agent.
        source = sb.filesystem.read_text("/work/candidate.rs")
        verifier.filesystem.write_text(source, "/final.rs")
        final = verifier.exec(
            "curl", "-s", "--fail-with-body", "--data-binary", "@/final.rs", "localhost:8080"
        )
        final.wait()
        print(final.stdout.read())
        verdict = "verified" if final.returncode == 0 else "rejected"
        print(f"Final candidate {verdict} in {time.monotonic() - start:.1f}s")
    finally:
        sb.terminate()
