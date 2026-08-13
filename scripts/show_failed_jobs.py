"""Print recent profile.extract job errors for debugging."""

import asyncio

from sqlalchemy import text

from launchkit.core.config import get_settings
from launchkit.persistence import create_database


async def main() -> None:
    settings = get_settings()
    database = create_database(settings)
    async with database.sessions() as session:
        rows = (
            await session.execute(
                text(
                    "select id, status, left(last_error, 800) as err, updated_at "
                    "from jobs where kind='profile.extract' "
                    "order by updated_at desc limit 3"
                )
            )
        ).all()
        for row in rows:
            print("----")
            print("job:", row[0], "status:", row[1], "at:", row[3])
            print("error:", row[2])
    await database.close()


if __name__ == "__main__":
    asyncio.run(main())
