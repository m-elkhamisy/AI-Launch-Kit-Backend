"""Print recent failed job errors for debugging (local or UAT DB)."""

import asyncio
import sys

from sqlalchemy import text

from launchkit.core.config import get_settings
from launchkit.persistence import create_database


async def main(kind: str | None = None) -> None:
    settings = get_settings()
    database = create_database(settings)
    async with database.sessions() as session:
        if kind:
            rows = (
                await session.execute(
                    text(
                        "select id, kind, status, left(last_error, 800) as err, updated_at "
                        "from jobs where kind = :kind and status = 'failed' "
                        "order by updated_at desc limit 10"
                    ),
                    {"kind": kind},
                )
            ).all()
        else:
            rows = (
                await session.execute(
                    text(
                        "select id, kind, status, left(last_error, 800) as err, updated_at "
                        "from jobs where status = 'failed' "
                        "order by updated_at desc limit 15"
                    )
                )
            ).all()
        if not rows:
            print("No failed jobs found.")
        for row in rows:
            print("----")
            print("job:", row[0], "kind:", row[1], "status:", row[2], "at:", row[4])
            print("error:", row[3])
    await database.close()


if __name__ == "__main__":
    filter_kind = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(filter_kind))
