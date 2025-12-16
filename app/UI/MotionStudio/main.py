from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(base_dir))

    from py.motionstudio_launcher import run  # noqa: E402

    return run(base_dir=base_dir)


if __name__ == "__main__":
    raise SystemExit(main())
