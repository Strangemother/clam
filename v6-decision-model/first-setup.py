#!/usr/bin/env python3
"""Create env/ and install the model server requirements."""

import os
from pathlib import Path
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parent
ENV_DIR = ROOT / "env"
REQUIREMENTS = ROOT / "requirements.txt"


def environment_python() -> Path:
    if os.name == "nt":
        return ENV_DIR / "Scripts" / "python.exe"
    return ENV_DIR / "bin" / "python"


def main() -> None:
    if not (3, 10) <= sys.version_info[:2] <= (3, 14):
        raise RuntimeError("Python 3.10 through 3.14 is required.")

    python = environment_python()
    if not ENV_DIR.exists():
        print(f"Creating virtual environment: {ENV_DIR}")
        venv.create(ENV_DIR, with_pip=True)
    if not python.is_file():
        raise RuntimeError(
            f"Virtual environment has no Python executable: {python}"
        )
    if not REQUIREMENTS.is_file():
        raise RuntimeError(f"Requirements file not found: {REQUIREMENTS}")

    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "-r",
            str(REQUIREMENTS),
        ],
        check=True,
    )
    print("Environment is ready.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Dependency installation failed: {exc}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
    except (OSError, RuntimeError) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
