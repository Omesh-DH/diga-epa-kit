from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = sorted((ROOT / "synthetic").glob("archetype_*/*.json"))

# Golden files and the validator suite build with this clock so output is stable.
FIXED_NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)


def synthetic_id(path: Path) -> str:
    return f"{path.parent.name}__{path.stem}"
