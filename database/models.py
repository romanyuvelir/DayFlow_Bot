import aiosqlite
from datetime import date, timedelta
from config import DB_PATH


# ═══════════════════════════════════════════════════════════════════════════════
#  UserModel
# ═══════════════════════════════════════════════════════════════════════════════

class UserModel:
    @staticmethod
    async def get_or_create(user_id: int, username: str, first_name: str) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name),
            )
            await db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
#  TaskModel
# ═══════════════════════════════════════════════════════════════════════════════

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
                """SELECT * FROM tasks
                   WHERE user_id = ? AND due_date = date('now')
                   ORDER BY is_done ASC, created_at ASC""",
                (user_id,),
            )
            return [dict(r) for r in await cursor.fetchall()]

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
                """UPDATE tasks SET is_done = 1, completed_at = CURRENT_TIMESTAMP
                   WHERE id = ? AND user_id = ? AND is_done = 0""",
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
            async def scalar(q: str, p: tuple = ()) -> int:
                cur = await db.execute(q, p)
                row = await cur.fetchone()
                return row[0] if row else 0

            total_today = await scalar(
                "SELECT COUNT(*) FROM tasks WHERE user_id=? AND due_date=date('now')", (user_id,))
            done_today = await scalar(
                "SELECT COUNT(*) FROM tasks WHERE user_id=? AND due_date=date('now') AND is_done=1", (user_id,))
            total_all = await scalar("SELECT COUNT(*) FROM tasks WHERE user_id=?", (user_id,))
            done_all  = await scalar("SELECT COUNT(*) FROM tasks WHERE user_id=? AND is_done=1", (user_id,))
            cur = await db.execute(
                """SELECT due_date, COUNT(*) cnt FROM tasks
                   WHERE user_id=? AND is_done=1
                   GROUP BY due_date ORDER BY cnt DESC LIMIT 1""", (user_id,))
            best = await cur.fetchone()
            return {
                "total_today": total_today, "done_today": done_today,
                "total_all": total_all,     "done_all": done_all,
                "best_day": best[0] if best else None,
                "best_day_count": best[1] if best else 0,
            }


# ═══════════════════════════════════════════════════════════════════════════════
#  ReminderModel
# ═══════════════════════════════════════════════════════════════════════════════

class ReminderModel:
    @staticmethod
    async def create(user_id: int, text: str, remind_at: str,
                     task_id: int | None = None) -> int:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO reminders (user_id, task_id, text, remind_at) VALUES (?, ?, ?, ?)",
                (user_id, task_id, text, remind_at),
            )
            await db.commit()
            return cursor.lastrowid  # type: ignore[return-value]

    @staticmethod
    async def get_pending_for_user(user_id: int) -> list[dict]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM reminders
                   WHERE user_id = ? AND is_sent = 0 AND remind_at > datetime('now')
                   ORDER BY remind_at ASC""",
                (user_id,),
            )
            return [dict(r) for r in await cursor.fetchall()]

    @staticmethod
    async def get_all_pending() -> list[dict]:
        """Used on startup to restore scheduler jobs."""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT * FROM reminders
                   WHERE is_sent = 0 AND remind_at > datetime('now')"""
            )
            return [dict(r) for r in await cursor.fetchall()]

    @staticmethod
    async def mark_sent(reminder_id: int) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE reminders SET is_sent = 1 WHERE id = ?", (reminder_id,))
            await db.commit()

    @staticmethod
    async def delete(reminder_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "DELETE FROM reminders WHERE id = ? AND user_id = ?",
                (reminder_id, user_id),
            )
            await db.commit()
            return cursor.rowcount > 0


# ═══════════════════════════════════════════════════════════════════════════════
#  FocusModel
# ═══════════════════════════════════════════════════════════════════════════════

class FocusModel:
    @staticmethod
    async def create_session(user_id: int, work_minutes: int,
                             break_minutes: int, session_type: str) -> int:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """INSERT INTO focus_sessions (user_id, work_minutes, break_minutes, session_type)
                   VALUES (?, ?, ?, ?)""",
                (user_id, work_minutes, break_minutes, session_type),
            )
            await db.commit()
            return cursor.lastrowid  # type: ignore[return-value]

    @staticmethod
    async def complete_session(session_id: int) -> None:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE focus_sessions SET completed = 1 WHERE id = ?", (session_id,))
            await db.commit()

    @staticmethod
    async def get_stats(user_id: int) -> dict:
        async with aiosqlite.connect(DB_PATH) as db:
            async def scalar(q: str, p: tuple = ()) -> int:
                cur = await db.execute(q, p)
                row = await cur.fetchone()
                return row[0] if row else 0

            total     = await scalar("SELECT COUNT(*) FROM focus_sessions WHERE user_id=?", (user_id,))
            completed = await scalar("SELECT COUNT(*) FROM focus_sessions WHERE user_id=? AND completed=1", (user_id,))
            total_min = await scalar(
                "SELECT COALESCE(SUM(work_minutes),0) FROM focus_sessions WHERE user_id=? AND completed=1", (user_id,))
            today_sessions = await scalar(
                """SELECT COUNT(*) FROM focus_sessions
                   WHERE user_id=? AND completed=1 AND date(started_at)=date('now')""", (user_id,))
            today_min = await scalar(
                """SELECT COALESCE(SUM(work_minutes),0) FROM focus_sessions
                   WHERE user_id=? AND completed=1 AND date(started_at)=date('now')""", (user_id,))
            return {
                "total": total, "completed": completed,
                "total_minutes": total_min,
                "today_sessions": today_sessions, "today_minutes": today_min,
            }


# ═══════════════════════════════════════════════════════════════════════════════
#  HabitModel
# ═══════════════════════════════════════════════════════════════════════════════

class HabitModel:
    @staticmethod
    async def create(user_id: int, name: str, emoji: str = "⭐") -> int:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO habits (user_id, name, emoji) VALUES (?, ?, ?)",
                (user_id, name, emoji),
            )
            await db.commit()
            return cursor.lastrowid  # type: ignore[return-value]

    @staticmethod
    async def get_active(user_id: int) -> list[dict]:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """SELECT h.*,
                       CASE WHEN hl.logged_date IS NOT NULL THEN 1 ELSE 0 END AS done_today
                   FROM habits h
                   LEFT JOIN habit_logs hl
                       ON h.id = hl.habit_id AND hl.logged_date = date('now')
                   WHERE h.user_id = ? AND h.is_active = 1
                   ORDER BY h.created_at ASC""",
                (user_id,),
            )
            return [dict(r) for r in await cursor.fetchall()]

    @staticmethod
    async def get_by_id(habit_id: int, user_id: int) -> dict | None:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM habits WHERE id = ? AND user_id = ? AND is_active = 1",
                (habit_id, user_id),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    async def delete(habit_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "UPDATE habits SET is_active = 0 WHERE id = ? AND user_id = ?",
                (habit_id, user_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    async def toggle_today(habit_id: int, user_id: int) -> bool:
        """Returns True if now done, False if now undone."""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT id FROM habit_logs WHERE habit_id=? AND user_id=? AND logged_date=date('now')",
                (habit_id, user_id),
            )
            existing = await cursor.fetchone()
            if existing:
                await db.execute(
                    "DELETE FROM habit_logs WHERE habit_id=? AND user_id=? AND logged_date=date('now')",
                    (habit_id, user_id),
                )
                await db.commit()
                return False
            else:
                await db.execute(
                    "INSERT OR IGNORE INTO habit_logs (habit_id, user_id) VALUES (?, ?)",
                    (habit_id, user_id),
                )
                await db.commit()
                return True

    @staticmethod
    async def get_stats(habit_id: int, user_id: int) -> dict:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """SELECT logged_date FROM habit_logs
                   WHERE habit_id = ? AND user_id = ?
                   ORDER BY logged_date DESC""",
                (habit_id, user_id),
            )
            rows = await cursor.fetchall()
            dates = [row[0] for row in rows]

            if not dates:
                return {"total": 0, "current_streak": 0,
                        "best_streak": 0, "done_today": False}

            today = date.today()
            date_set = {date.fromisoformat(d) for d in dates}
            done_today = today in date_set

            # Current streak (count back from today)
            current_streak = 0
            check = today
            while check in date_set:
                current_streak += 1
                check -= timedelta(days=1)

            # Best streak (scan sorted list)
            sorted_dates = sorted(date_set)
            best_streak, streak = 1, 1
            for i in range(1, len(sorted_dates)):
                if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                    streak += 1
                    best_streak = max(best_streak, streak)
                else:
                    streak = 1
            best_streak = max(best_streak, streak)

            return {
                "total": len(dates),
                "current_streak": current_streak,
                "best_streak": best_streak,
                "done_today": done_today,
            }

    @staticmethod
    async def get_overall_stats(user_id: int) -> dict:
        async with aiosqlite.connect(DB_PATH) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM habits WHERE user_id=? AND is_active=1", (user_id,))
            total_habits = (await cur.fetchone())[0]
            cur = await db.execute(
                "SELECT COUNT(*) FROM habit_logs WHERE user_id=? AND logged_date=date('now')", (user_id,))
            done_today = (await cur.fetchone())[0]
            cur = await db.execute(
                "SELECT COUNT(DISTINCT logged_date) FROM habit_logs WHERE user_id=?", (user_id,))
            active_days = (await cur.fetchone())[0]
            cur = await db.execute(
                "SELECT COUNT(*) FROM habit_logs WHERE user_id=?", (user_id,))
            total_logs = (await cur.fetchone())[0]
            return {
                "total_habits": total_habits,
                "done_today": done_today,
                "active_days": active_days,
                "total_logs": total_logs,
            }