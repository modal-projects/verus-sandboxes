"""Keep the model key in a Sidecar. The main Sandbox can only reach the proxy."""

from urllib.parse import urlsplit

import modal

from support.model import load_endpoint

image = modal.Image.debian_slim().apt_install("curl")
caddy = modal.Image.from_registry("caddy:2.11")
app = modal.App("sandbox-proxy")


def status(sb: modal.Sandbox, url: str) -> str:
    """Result of a request sent with an invalid key."""
    p = sb.exec(
        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-m", "15",
        "-H", "Authorization: Bearer invalid", url, timeout=20,
    )  # fmt: skip
    p.wait()
    code = p.stdout.read()
    return "no connection" if code == "000" else f"HTTP {code}"  # 000: no response at all.


@app.local_entrypoint()
def main():
    endpoint = load_endpoint()
    path = urlsplit(endpoint.url).path
    caddy.build(app)  # Sidecar images must be built before the Sidecar is created.
    sb = modal.Sandbox.create(
        app=app,
        image=image,
        timeout=5 * 60,
        outbound_cidr_allowlist=[],  # No external traffic; Sidecars stay reachable.
    )
    try:
        sb._experimental_sidecars.create(
            "sh",
            "-c",
            'exec caddy reverse-proxy --from :8080 --to "https://$1" --change-host-header'
            ' --header-up "Authorization: Bearer $MODEL_KEY"',
            "proxy",
            endpoint.host,
            name="proxy",
            image=caddy,
            secrets=[modal.Secret.from_dict({"MODEL_KEY": endpoint.key})],
            outbound_domain_allowlist=[endpoint.host],
        )
        sb.exec("bash", "-c", "until echo > /dev/tcp/proxy/8080; do sleep 0.1; done").wait()

        key_present = sb.exec("sh", "-c", 'test -n "${MODEL_KEY+x}"').wait() == 0
        direct = status(sb, f"{endpoint.url}/models")
        proxied = status(sb, f"http://proxy:8080{path}/models")
        print(f"Key in main Sandbox: {'present' if key_present else 'absent'}")
        print(f"Direct to endpoint:  {direct}")
        print(f"Through the proxy:   {proxied}")
        assert not key_present and direct == "no connection" and proxied == "HTTP 200"
    finally:
        sb.terminate()
