#!/usr/bin/env python3
"""Create a planned experiment record. Never execute a simulator or policy."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import shutil


REGISTRY_FIELDS = ["experiment_id", "title", "status", "created_at_utc", "record_path", "config_sha256"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, dest="experiment_id", help="1-64 letters, digits, underscores or hyphens; start with a letter/digit.")
    parser.add_argument("--title", required=True, help="Brief purpose of the proposed experiment.")
    parser.add_argument("--config", default="configs/pilot.template.json", help="JSON config, relative to project root unless absolute.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Project root; defaults to this script's repository.")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", args.experiment_id):
        parser.error("Invalid experiment ID; slashes, dot segments and whitespace are not allowed.")
    if not args.title.strip() or "\n" in args.title or "\r" in args.title:
        parser.error("Title must be nonempty and contain a single line.")

    root = args.root.resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    registry = root / "experiments" / "registry.csv"
    template = root / "templates" / "experiment.md"
    try:
        config_bytes = config_path.read_bytes()
        config = json.loads(config_bytes)
        if not isinstance(config, dict):
            parser.error("Config must be a JSON object.")
        record_template = template.read_text(encoding="utf-8")
        with registry.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != REGISTRY_FIELDS:
                parser.error("Registry header does not match this tool's schema.")
            rows = list(reader)
        if any(row["experiment_id"] == args.experiment_id for row in rows):
            parser.error("Experiment ID already appears in the registry; choose another ID.")
    except (OSError, UnicodeError, json.JSONDecodeError):
        parser.error("Could not read config, template or registry; run against a complete project scaffold with valid JSON.")

    runs = root / "experiments" / "runs"
    if runs.is_symlink() or (runs.exists() and runs.resolve().parent != (root / "experiments").resolve()):
        parser.error("Refusing a redirected experiments/runs directory.")
    if (root / "experiments").is_symlink() or registry.is_symlink():
        parser.error("Refusing redirected experiment storage.")
    destination = runs / args.experiment_id
    created_at = datetime.now(timezone.utc).isoformat()
    config_hash = hashlib.sha256(config_bytes).hexdigest()
    metadata = {
        "schema_version": "0.1",
        "experiment_id": args.experiment_id,
        "title": args.title.strip(),
        "status": "planned",
        "created_at_utc": created_at,
        "config_file": "config.json",
        "config_sha256": config_hash,
        "execution_started_at_utc": None,
        "execution_finished_at_utc": None,
        "code_commit": None,
        "environment_record": None,
        "raw_artifacts": [],
        "metrics": None,
        "note": "Planning record only. No simulation, policy evaluation or metric computation has been performed by this tool.",
    }
    record = (record_template.replace("{{EXPERIMENT_ID}}", args.experiment_id)
              .replace("{{TITLE}}", args.title.strip()).replace("{{CREATED_AT}}", created_at))
    entry = {
        "experiment_id": args.experiment_id,
        "title": args.title.strip(),
        "status": "planned",
        "created_at_utc": created_at,
        "record_path": destination.relative_to(root).as_posix(),
        "config_sha256": config_hash,
    }
    try:
        runs.mkdir(exist_ok=True)
        destination.mkdir()
    except FileExistsError:
        parser.error("Experiment directory already exists; nothing was overwritten.")
    except OSError:
        parser.error("Could not create experiment directory.")
    try:
        (destination / "config.json").write_bytes(config_bytes)
        (destination / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (destination / "record.md").write_text(record, encoding="utf-8")
    except OSError:
        shutil.rmtree(destination)
        parser.error("Could not write planning record; new directory was removed.")
    try:
        buffer = io.StringIO(newline="")
        csv.DictWriter(buffer, fieldnames=REGISTRY_FIELDS, lineterminator="\n").writerow(entry)
        with registry.open("a", newline="", encoding="utf-8") as handle:
            handle.write(buffer.getvalue())
    except OSError:
        parser.error("Record was created, but registry update failed; inspect it before retrying.")
    print(json.dumps({"status": "planned", "record_path": entry["record_path"], "simulation_executed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
