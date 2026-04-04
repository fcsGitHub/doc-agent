"""Development utility to reset the database and re-seed demo data."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from scripts.seed import seed_database


async def _run_alembic(command: str) -> None:
    process = await asyncio.create_subprocess_exec(
        "alembic",
        command,
        "base" if command == "downgrade" else "head",
        cwd=str(Path(__file__).resolve().parents[1]),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if stdout:
        print(stdout.decode().strip())
    if stderr:
        print(stderr.decode().strip(), file=sys.stderr)
    if process.returncode != 0:
        raise RuntimeError(
            f"alembic {command} failed with exit code {process.returncode}"
        )


async def reset_database() -> None:
    """Drop and recreate the schema, then re-seed."""

    await _run_alembic("downgrade")
    await _run_alembic("upgrade")
    _ = await seed_database()


def main() -> int:
    asyncio.run(reset_database())
    print("[reset-db] Database reset and seeded successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
