"""Download helper shared by the tooling scripts.

Prefers curl when it is on PATH: on machines with an HTTPS-intercepting proxy
the OS trust store (which curl uses on Windows) often has the proxy CA while
Python's does not. Falls back to urllib otherwise. Never disables TLS checks.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    print(f"downloading {url}", file=sys.stderr)
    if shutil.which("curl"):
        subprocess.run(["curl", "-fsSL", "-o", str(tmp), url], check=True)
    else:
        urllib.request.urlretrieve(url, tmp)
    tmp.replace(dest)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
