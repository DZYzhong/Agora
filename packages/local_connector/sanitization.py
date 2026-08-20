from __future__ import annotations

import re
from urllib.parse import urlsplit

from packages.domain.local_workspace import RepositoryIdentity


def normalize_repository_identity(remote: str | None) -> RepositoryIdentity | None:
    if not remote:
        return None
    value = remote.strip()
    if not value:
        return None

    host: str | None = None
    path: str | None = None

    if "://" in value:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        path = parsed.path.lstrip("/")
    else:
        match = re.match(r"^(?:(?P<user>[^@/:]+)@)?(?P<host>[^:]+):(?P<path>.+)$", value)
        if match:
            host = match.group("host").lower()
            path = match.group("path")
        else:
            cleaned = value.removeprefix("git@")
            parts = cleaned.split("/", 1)
            if len(parts) == 2:
                host = parts[0].lower()
                path = parts[1]

    if not host or not path:
        return None

    path = path.strip("/").removesuffix(".git").lower()
    host = host.strip().lower()
    if not host or not path or "@" in host or "@" in path:
        return None
    normalized = f"{host}/{path}"
    return RepositoryIdentity(host=host, path=path, normalized=normalized)


def scrub_remote(remote: str | None) -> str | None:
    identity = normalize_repository_identity(remote)
    return identity.normalized if identity else None
