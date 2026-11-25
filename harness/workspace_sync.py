"""Shared entrypoint for marker-preserving transient workspace synchronization."""

import pathlib
import sys

# Run directly (a kickoff Validator does), Python sees only harness/, not factory_runtime.
_PACKAGE_ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if _PACKAGE_ROOT not in sys.path:
    sys.path.append(_PACKAGE_ROOT)

from factory_runtime.kindex_workspace import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
