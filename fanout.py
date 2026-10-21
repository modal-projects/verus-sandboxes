"""Run 500 independent Verus checks in parallel and report the total time."""

import asyncio
import time

import modal

from verify import ROOT
from verify import image as verus_image

# Bake the inputs into the image so each Sandbox starts verifying immediately.
image = (
    verus_image.add_local_file(ROOT / "contract/main.rs", "/task/main.rs", copy=True)
    .add_local_file(ROOT / "contract/spec.rs", "/task/spec.rs", copy=True)
    .add_local_file(ROOT / "contract/solution.rs", "/task/candidate.rs", copy=True)
)
app = modal.App("verus-fanout")


async def verify_one() -> bool:
    sb = await modal.Sandbox.create.aio(
        "verus",
        "--no-cheating",
        "/task/main.rs",
        app=app,
        image=image,
        timeout=5 * 60,
        block_network=True,
    )
    try:
        await sb.wait.aio()
        return sb.returncode == 0
    finally:
        await sb.terminate.aio()


@app.local_entrypoint()
async def main(count: int = 500):
    await image.build.aio(app)
    print(f"Launching {count} Sandboxes...", flush=True)
    start = time.monotonic()
    results = await asyncio.gather(*(verify_one() for _ in range(count)), return_exceptions=True)
    print(f"{results.count(True)}/{count} verified in {time.monotonic() - start:.1f}s")
    errors = [r for r in results if isinstance(r, BaseException)]
    if errors:
        print(f"{len(errors)} Sandboxes raised. First error: {errors[0]!r}")
