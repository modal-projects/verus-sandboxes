"""Send one request from each of several Sandboxes to the same model endpoint."""

import asyncio
import json
import time

import modal

from support.model import load_endpoint

image = modal.Image.debian_slim().apt_install("curl")
app = modal.App("sandbox-endpoint")

REQUEST = """curl -sS -m 120 -o /dev/null -w "HTTP %{http_code} in %{time_total}s" \
  "$MODEL_URL/chat/completions" -H "Authorization: Bearer $MODEL_KEY" \
  -H "Content-Type: application/json" --data-binary "$1"
"""


async def ask(endpoint, secret: modal.Secret) -> str:
    sb = await modal.Sandbox.create.aio(
        app=app,
        image=image,
        timeout=5 * 60,
        secrets=[secret],
        outbound_domain_allowlist=[endpoint.host],  # The model host only.
    )
    try:
        body = {
            "model": endpoint.model,
            "messages": [{"role": "user", "content": "Say hello in one sentence."}],
            "max_tokens": 128,
        }
        p = await sb.exec.aio("sh", "-c", REQUEST, "request", json.dumps(body), timeout=150)
        await p.wait.aio()
        return await p.stdout.read.aio() + await p.stderr.read.aio()
    finally:
        await sb.terminate.aio()


@app.local_entrypoint()
async def main(count: int = 4):
    endpoint = load_endpoint()
    secret = modal.Secret.from_dict({"MODEL_URL": endpoint.url, "MODEL_KEY": endpoint.key})
    await image.build.aio(app)
    start = time.monotonic()
    results = await asyncio.gather(*(ask(endpoint, secret) for _ in range(count)))
    for i, result in enumerate(results, start=1):
        print(f"Sandbox {i}: {result.strip()}")
    print(f"{count} requests in {time.monotonic() - start:.1f}s")
