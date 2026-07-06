import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN
from database.db import init_db
from database.models import ReminderModel
from handlers import focus, habits, reminders, start, stats, tasks
from handlers.reminders import _job_send_reminder
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def restore_pending_reminders(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Re-schedule all reminders that survived a bot restart."""
    pending = await ReminderModel.get_all_pending()
    for r in pending:
        run_date = datetime.strptime(r["remind_at"], "%Y-%m-%d %H:%M:%S")
        scheduler.add_job(
            _job_send_reminder,
            trigger="date",
            run_date=run_date,
            kwargs={
                "bot": bot,
                "user_id": r["user_id"],
                "reminder_id": r["id"],
                "text": r["text"],
            },
            id=f"reminder_{r['id']}",
            replace_existing=True,
        )
    if pending:
        logger.info(f"Restored {len(pending)} pending reminder(s).")


async def main() -> None:
    await init_db()
    logger.info("Database initialized.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    scheduler = AsyncIOScheduler()
    scheduler.start()
    logger.info("Scheduler started.")

    await restore_pending_reminders(scheduler, bot)

    dp = Dispatcher(storage=MemoryStorage())

    # Inject bot + scheduler into all handlers via dependency injection
    dp.workflow_data.update({"scheduler": scheduler, "bot": bot})

    dp.include_router(start.router)
    dp.include_router(tasks.router)
    dp.include_router(stats.router)
    dp.include_router(reminders.router)
    dp.include_router(focus.router)
    dp.include_router(habits.router)

    logger.info("DayFlowBot is running...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())