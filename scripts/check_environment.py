#!/usr/bin/env python3
"""Read installed-package metadata only; do not import or run simulators."""

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform


PACKAGES = ("pybullet", "Pillow", "mani-skill", "sapien", "mujoco", "robosuite", "rlbench", "pyrep", "torch", "numpy")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write a new JSON file; refuse to overwrite an existing file.")
    args = parser.parse_args()
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = {"installed": True, "version": importlib.metadata.version(name)}
        except importlib.metadata.PackageNotFoundError:
            versions[name] = {"installed": False, "version": None}
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "This machine only; package metadata is not a usability or rendering check.",
        "python_version": platform.python_version(),
        "operating_system": platform.system(),
        "architecture": platform.machine(),
        "packages": versions,
        "simulator_execution": "not_run",
        "rendering_validation": "not_run",
        "gpu_validation": "not_run",
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        try:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(output)
        except FileExistsError:
            parser.error("Output already exists; choose a new filename.")
        except OSError:
            parser.error("Could not create output; ensure its parent directory exists and is writable.")
    print(output, end="")


if __name__ == "__main__":
    main()
