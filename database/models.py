import aiosqlite
from config import DB_PATH


class UserModel:
    @staticmethod
    async def get_or_create(user_id: int, username: str, first_name: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name),
            )
            await db.commit()


class TaskModel:
    @staticmethod
    async def add_task(user_id: int, title: str, description: str | None = None) -> int:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO tasks (user_id, title, description, due_date) VALUES (?, ?, ?, date('now'))",
                (user_id, title, description),
            )
            await db.commit()
            return cursor.lastrowid  # type: ignore[return-value]

    @staticmethod
    async def get_today_tasks(user_id: int) -> list[dict]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM tasks
                WHERE user_id = ? AND due_date = date('now')
                ORDER BY is_done ASC, created_at ASC
                """,
                (user_id,),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    async def get_task_by_id(task_id: int, user_id: int) -> dict | None:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def complete_task(task_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                UPDATE tasks
                SET is_done = 1, completed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ? AND is_done = 0
                """,
                (task_id, user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    async def delete_task(task_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    async def get_stats(user_id: int) -> dict:
        async with aiosqlite.connect(DB_PATH) as db:
            async def scalar(query: str, params: tuple = ()) -> int:
                cur = await db.execute(query, params)
                row = await cur.fetchone()
                return row[0] if row else 0

            total_today = await scalar(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND due_date = date('now')",
                (user_id,),
            )
            done_today = await scalar(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND due_date = date('now') AND is_done = 1",
                (user_id,),
            )
            total_all = await scalar(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ?",
                (user_id,),
            )
            done_all = await scalar(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND is_done = 1",
                (user_id,),
            )

            cur = await db.execute(
                """
                SELECT due_date, COUNT(*) AS cnt FROM tasks
                WHERE user_id = ? AND is_done = 1
                GROUP BY due_date
                ORDER BY cnt DESC
                LIMIT 1
                """,
                (user_id,),
            )
            best = await cur.fetchone()

            return {
                "total_today": total_today,
                "done_today": done_today,
                "total_all": total_all,
                "done_all": done_all,
                "best_day": best[0] if best else None,
                "best_day_count": best[1] if best else 0,
            }
