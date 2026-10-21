"""Compare open, blocked, and allowlisted outbound access."""

import modal

HOSTS = ["https://modal.com", "https://example.com"]
# Name, Sandbox arguments, and whether each host should be reachable.
POLICIES = [
    ("open", {}, [True, True]),
    ("blocked", {"block_network": True}, [False, False]),
    ("allowlist", {"outbound_domain_allowlist": ["modal.com"]}, [True, False]),
]

image = modal.Image.debian_slim().apt_install("curl")
app = modal.App("sandbox-network")


def reachable(sb: modal.Sandbox, url: str) -> bool:
    p = sb.exec("curl", "-s", "-o", "/dev/null", "-m", "5", url, timeout=20)
    return p.wait() == 0  # curl exits 0 on any HTTP response, nonzero if it cannot connect.


@app.local_entrypoint()
def main():
    for name, policy, expected in POLICIES:
        sb = modal.Sandbox.create(app=app, image=image, timeout=2 * 60, **policy)
        try:
            for host, want in zip(HOSTS, expected):
                got = reachable(sb, host)
                print(f"{name:9} {host:20} {'reachable' if got else 'unreachable'}")
                assert got == want, f"{name}: expected {host} reachable={want}"
        finally:
            sb.terminate()
