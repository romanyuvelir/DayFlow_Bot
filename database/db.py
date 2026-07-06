import aiosqlite
from config import DB_PATH


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        # ── existing ──────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT    DEFAULT '',
                first_name TEXT    DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                title        TEXT    NOT NULL,
                description  TEXT,
                is_done      INTEGER DEFAULT 0,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                due_date     DATE DEFAULT (date('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        # ── reminders ─────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                task_id     INTEGER,
                text        TEXT    NOT NULL,
                remind_at   TIMESTAMP NOT NULL,
                is_sent     INTEGER DEFAULT 0,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
            )
        """)
        # ── focus sessions ────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS focus_sessions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                work_minutes   INTEGER NOT NULL,
                break_minutes  INTEGER NOT NULL,
                session_type   TEXT    DEFAULT 'custom',
                started_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed      INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        # ── habits ────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                name       TEXT    NOT NULL,
                emoji      TEXT    DEFAULT '⭐',
                is_active  INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS habit_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id    INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                logged_date DATE DEFAULT (date('now')),
                UNIQUE(habit_id, logged_date),
                FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
            )
        """)
        await db.commit()