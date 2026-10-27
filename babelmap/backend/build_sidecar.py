"""Freeze ``babelmap/backend/server.py`` into the Tauri sidecar binary.

The packaged app must not depend on a Python installation: this script produces
a single self-contained executable that Tauri ships as an ``externalBin``
sidecar next to ``BabelMap.exe``.  The data tree is *not* frozen into the
binary — it ships as a Tauri resource and is handed to the backend through
``BABELSOFT_DATA_DIR`` (see ``src-tauri/src/lib.rs``).

Usage (from the repo root, in the project venv)::

    python babelmap/backend/build_sidecar.py            # release build
    python babelmap/backend/build_sidecar.py --debug    # keep the build dir

The output is ``babelmap/src-tauri/binaries/babelmap-backend-<target-triple>.exe``,
which is exactly the name Tauri expects for ``externalBin``.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BABELLIB = REPO_ROOT / "babellib"
SRC_TAURI = REPO_ROOT / "babelmap" / "src-tauri"
ENTRY_POINT = REPO_ROOT / "babelmap" / "backend" / "server.py"
WORK_DIR = REPO_ROOT / "build" / "sidecar"

#: Native wheels whose binaries/data files PyInstaller must carry over whole.
COLLECT_ALL = (
    "uharfbuzz",
    "freetype",
    "pyusp",
    "pydwshape",
    "pygraphite2",
    "pyyudit",
    "pyharfrust2",
)


def target_triple() -> str:
    """The host triple Tauri uses in sidecar file names (``rustc -vV``)."""
    try:
        out = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - no toolchain
        raise SystemExit(f"rustc not found; install the Rust toolchain first ({exc})") from exc
    for line in out.splitlines():
        if line.startswith("host: "):
            return line.split(":", 1)[1].strip()
    raise SystemExit("could not read the host triple from rustc -vV")


def build(debug: bool = False) -> Path:
    triple = target_triple()
    suffix = ".exe" if sys.platform == "win32" else ""
    out_dir = SRC_TAURI / "binaries"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"babelmap-backend-{triple}"

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        out_name,
        "--distpath",
        str(out_dir),
        "--workpath",
        str(WORK_DIR),
        "--specpath",
        str(WORK_DIR),
        "--paths",
        str(BABELLIB),
        "--paths",
        str(REPO_ROOT),
        # Lazily imported by the engine modules, so PyInstaller cannot see them.
        "--hidden-import",
        "uvicorn.logging",
        "--hidden-import",
        "uvicorn.loops.auto",
        "--hidden-import",
        "uvicorn.protocols.http.auto",
        "--hidden-import",
        "uvicorn.protocols.websockets.auto",
        "--hidden-import",
        "uvicorn.lifespan.on",
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "tkinter",
        "--exclude-module",
        "matplotlib",
    ]
    for package in COLLECT_ALL:
        args += ["--collect-all", package]
    args.append(str(ENTRY_POINT))

    print(f"[sidecar] freezing {ENTRY_POINT.name} -> {out_dir / (out_name + suffix)}")
    subprocess.run(args, check=True, cwd=REPO_ROOT)

    built = out_dir / (out_name + suffix)
    if not built.is_file():
        raise SystemExit(f"PyInstaller did not produce {built}")
    if not debug:
        shutil.rmtree(WORK_DIR, ignore_errors=True)
    print(f"[sidecar] {built} ({built.stat().st_size / 1e6:.1f} MB)")
    return built


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--debug", action="store_true", help="keep PyInstaller's work directory")
    build(debug=parser.parse_args(argv).debug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
