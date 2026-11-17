"""Prepare the try-it page in site/ for GitHub Pages or a local preview.

Usage: python scripts/build_site.py [OUT_DIR]

Writes two generated files next to the page (default: site/):
- diga_epa_kit.zip: the kit's source and the page's bridge module, unpacked
  by Pyodide in the visitor's browser;
- examples.json: the synthetic inputs, offered on the page as examples.

Needs only the standard library, so CI can run it without installing the kit.

Anonymous usage counting is off unless DIGA_SITE_COUNTER holds a GoatCounter
count address (https://CODE.goatcounter.com/count); the Pages workflow takes
it from the repository variable GOATCOUNTER_URL. http://localhost:PORT/count
is accepted for testing the page.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
ARCHETYPES = {
    "archetype_a_mental": "A · mental health",
    "archetype_b_metabolic": "B · metabolic",
    "archetype_c_pain": "C · pain",
    "archetype_d_exercise": "D · exercise",
}


def _label(path: Path) -> str:
    group = ARCHETYPES.get(path.parent.name, path.parent.name)
    return f"{group}: {path.stem.replace('_', ' ')}"


_COUNTER = re.compile(r"^(https://[a-z0-9][a-z0-9-]*\.goatcounter\.com|http://localhost:\d{2,5})/count$")


def _counter() -> str | None:
    url = os.environ.get("DIGA_SITE_COUNTER", "").strip()
    if url and not _COUNTER.fullmatch(url):
        print(f"ignoring DIGA_SITE_COUNTER {url!r}: not a GoatCounter count address", file=sys.stderr)
        return None
    return url or None


def _git_rev() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else SITE
    out.mkdir(parents=True, exist_ok=True)
    if out != SITE:
        for name in ("index.html", "app.js", "style.css"):
            shutil.copy2(SITE / name, out / name)

    with zipfile.ZipFile(out / "diga_epa_kit.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted((ROOT / "src" / "diga_epa_kit").rglob("*.py")):
            z.write(path, path.relative_to(ROOT / "src").as_posix())
        z.write(SITE / "trykit.py", "trykit.py")

    build = [
        {"label": _label(p), "data": json.loads(p.read_text(encoding="utf-8"))}
        for p in sorted((ROOT / "synthetic").glob("archetype_*/*.json"))
    ]
    eml = ROOT / "synthetic" / "epa_import" / "medication_list.json"
    # A regex, not tomllib: the script must also run on Python 3.10.
    match = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    version = match.group(1) if match else "unknown"
    examples = {
        "meta": {
            "kit_version": version,
            "git_rev": _git_rev(),
            "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "counter": _counter(),
        },
        "build": build,
        "import": [{"label": "Synthetic ePA medication list", "data": json.loads(eml.read_text(encoding="utf-8"))}],
    }
    (out / "examples.json").write_text(json.dumps(examples, ensure_ascii=False), encoding="utf-8")
    counting = "on" if examples["meta"]["counter"] else "off"
    rev = examples["meta"]["git_rev"]
    print(f"site ready in {out}: {len(build)} examples, kit {version} ({rev}), counting {counting}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
