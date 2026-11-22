#!/usr/bin/env python3
"""Set up the environment, then launch the D1 Omni server."""

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
ENV_DIR = ROOT / "env"


def environment_python() -> Path:
    if os.name == "nt":
        return ENV_DIR / "Scripts" / "python.exe"
    return ENV_DIR / "bin" / "python"


def main() -> None:
    setup = subprocess.run(
        [sys.executable, str(ROOT / "first-setup.py")],
        check=False,
    )
    if setup.returncode:
        raise SystemExit(setup.returncode)

    server = subprocess.run(
        [
            str(environment_python()),
            str(ROOT / "server.py"),
            *sys.argv[1:],
        ],
        check=False,
    )
    raise SystemExit(server.returncode)


if __name__ == "__main__":
    try:
        main()
    except OSError as exc:
        print(f"Could not start the model server: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
