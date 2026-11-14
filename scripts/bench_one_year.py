"""Size and speed test: one synthetic patient, one year of data, one bundle.

Usage: python scripts/bench_one_year.py [--validate] [--record] [--keep FILE]

Generates the input in memory with a fixed seed (synthetic data only), then
times input validation, bundle building, the local checks and serialisation.
``--validate`` also runs the HL7 validator on the result (several minutes,
needs Java). ``--record`` appends the figures to research/benchmarks.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fetch_spec import locked, tgz_path
from validate import VALIDATOR_VERSION, ensure_jar, git_rev

from diga_epa_kit import DigaExport, build_bundle, check_bundle, validate

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "research" / "benchmarks.csv"
START = date(2025, 11, 1)
DAYS = 365
NOW = datetime(2026, 11, 1, 9, 0, tzinfo=timezone.utc)
# A fixed offset keeps the generator simple; real exports carry the local offset.
TZ = timezone(timedelta(hours=1))


def one_year_input(seed: int = 20261114) -> dict[str, Any]:
    rng = random.Random(seed)
    days = [START + timedelta(days=n) for n in range(DAYS)]

    def at(day: date, hour: int, minute: int) -> str:
        return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ).isoformat()

    weight = 96.0
    weights, bmis, pressures, rates, steps, diary, scores = [], [], [], [], [], [], []
    for n, day in enumerate(days):
        weight = max(70.0, weight + rng.uniform(-0.25, 0.2))
        weights.append({"measured_at": at(day, 7, 10), "kg": round(weight, 1)})
        pressures.append(
            {"measured_at": at(day, 7, 15), "systolic": rng.randint(122, 148), "diastolic": rng.randint(76, 94)}
        )
        rates.append({"measured_at": at(day, 7, 15), "bpm": rng.randint(58, 88)})
        steps.append({"day": day.isoformat(), "steps": rng.randint(1500, 12000)})
        if n % 7 == 0:
            bmis.append({"measured_at": at(day, 7, 10), "kg_m2": round(weight / 1.72**2, 1)})
        if n % 14 == 0:
            scores.append({"instrument": "phq9", "completed_at": at(day, 19, 30), "score": rng.randint(2, 16)})
            scores.append({"instrument": "gad7", "completed_at": at(day, 19, 40), "score": rng.randint(1, 13)})
        if n % 7 in (1, 3, 5):
            diary.append({"written_at": at(day, 20, 45), "text": f"Synthetischer Tagebucheintrag {n + 1}."})

    return {
        "diga": {
            "name": "Synthetic Year Coach",
            "ve_id": "99990009",
            "version": "4.0.0",
            "pzn": "19999990",
            "manufacturer": {"name": "Synthetic DiGA GmbH", "website": "https://example.org"},
        },
        "patient": {"id": "0c7d5e1a-9b34-4a6f-8e21-7f3a2b4c5d60", "birth_date": "1971-04-12", "gender": "female"},
        "period_start": days[0].isoformat(),
        "period_end": days[-1].isoformat(),
        "body_weights": weights,
        "body_heights": [{"measured_at": at(days[0], 7, 0), "cm": 172.0}],
        "blood_pressures": pressures,
        "heart_rates": rates,
        "body_mass_indices": bmis,
        "daily_steps": steps,
        "prom_scores": scores,
        "diary_entries": diary,
        "goals": [
            {
                "id": "goal-weight",
                "description": "Synthetisches Gewichtsziel",
                "status": "active",
                "start": "2025-11-01",
            },
            {"id": "goal-steps", "description": "Synthetisches Schrittziel", "status": "active", "start": "2025-11-01"},
        ],
    }


def timed(fn: Any) -> tuple[Any, float]:
    t0 = time.perf_counter()
    out = fn()
    return out, time.perf_counter() - t0


def measure(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    data, t_input = timed(lambda: DigaExport.model_validate(raw))
    bundle, t_build = timed(lambda: build_bundle(data, now=NOW))
    problems, t_check = timed(lambda: check_bundle(bundle))
    text, t_dump = timed(lambda: json.dumps(bundle, ensure_ascii=False))
    figures = {
        "resources": len(bundle["entry"]),
        "bytes": len(text.encode("utf-8")),
        "input_s": round(t_input, 3),
        "build_s": round(t_build, 3),
        "check_s": round(t_check, 3),
        "dump_s": round(t_dump, 3),
        "check_problems": len(problems),
    }
    return bundle, figures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--keep", help="write the bundle to this file")
    args = parser.parse_args()

    bundle, figures = measure(one_year_input())
    figures.update({"validator_s": "", "errors": "", "warnings": "", "timeouts": ""})
    if args.keep:
        Path(args.keep).write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    if args.validate:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "one-year.json"
            path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
            report, t_val = timed(
                lambda: validate(path, jar=ensure_jar(VALIDATOR_VERSION), packages=[tgz_path(p) for p in locked()])
            )
        figures.update(
            {
                "validator_s": round(t_val, 1),
                "errors": len(report.errors),
                "warnings": len(report.warnings),
                "timeouts": len(report.timeouts),
            }
        )
        for i in report.errors[:20]:
            print(f"ERROR {i.location}: {i.message}")
    for k, v in figures.items():
        print(f"{k}: {v}")

    if args.record:
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git_rev": git_rev(),
            "python": platform.python_version(),
            "machine": platform.machine(),
            **figures,
        }
        new = not RESULTS.exists()
        with RESULTS.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)
    bad = figures["check_problems"] or figures["errors"] or figures["timeouts"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
