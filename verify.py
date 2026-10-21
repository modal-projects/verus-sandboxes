"""Verify one implementation against the contract in a Sandbox without network access."""

import time
from pathlib import Path

import modal

ROOT = Path(__file__).parent
VERUS = "0.2026.10.18.7d82994"
TOOLCHAIN = "1.99.1-x86_64-unknown-linux-gnu"  # Must match the Verus release.
RELEASE = f"https://github.com/verus-lang/verus/releases/download/release/{VERUS}"

image = (
    modal.Image.from_registry("ubuntu:24.04")  # The bundled Z3 needs a recent glibc.
    .apt_install("curl", "unzip")
    .run_commands(
        "curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal"
        f" --default-toolchain {TOOLCHAIN} -c rustc-dev -c llvm-tools",
        f"curl -fsSL -o /tmp/verus.zip {RELEASE}/verus-{VERUS}-x86-linux.zip"
        " && unzip -q /tmp/verus.zip -d /opt"
        " && mv /opt/verus-x86-linux /opt/verus && rm /tmp/verus.zip",
        "/opt/verus/z3 --version",
    )
    .env({"PATH": "/opt/verus:/root/.cargo/bin:/usr/local/bin:/usr/bin:/bin"})
)

app = modal.App("verus-verify")


@app.local_entrypoint()
def main(path: str = "contract/solution.rs"):
    sb = modal.Sandbox.create(app=app, image=image, timeout=5 * 60, block_network=True)
    try:
        # File uploads go through the Modal API, so they work with the network blocked.
        for name in ("main.rs", "spec.rs"):
            sb.filesystem.write_text((ROOT / "contract" / name).read_text(), f"/{name}")
        sb.filesystem.write_text((ROOT / path).read_text(), "/candidate.rs")
        start = time.monotonic()
        p = sb.exec("verus", "--no-cheating", "/main.rs", timeout=120)
        p.wait()
        print(p.stdout.read() + p.stderr.read())
        verdict = "verified" if p.returncode == 0 else "rejected"
        print(f"{path}: {verdict} in {time.monotonic() - start:.1f}s")
    finally:
        sb.terminate()
