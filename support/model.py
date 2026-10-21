"""The model endpoint used by endpoint.py, proxy.py, and agent.py, read from .env."""

import os
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit

ENV_FILE = Path(__file__).parent.parent / ".env"


class Endpoint(NamedTuple):
    url: str  # OpenAI-compatible base URL, ending in /v1.
    key: str
    model: str

    @property
    def host(self) -> str:
        return urlsplit(self.url).hostname


def load_endpoint() -> Endpoint:
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                name, value = line.split("=", 1)
                values[name.strip()] = value.strip().strip("\"'")
    values.update({k: v for k, v in os.environ.items() if k.startswith("MODEL_")})
    missing = [k for k in ("MODEL_URL", "MODEL_KEY", "MODEL_NAME") if not values.get(k)]
    if missing:
        raise ValueError(f"Set {', '.join(missing)} in .env. See .env.example.")
    return Endpoint(values["MODEL_URL"].rstrip("/"), values["MODEL_KEY"], values["MODEL_NAME"])
