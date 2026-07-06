import logging
from datetime import datetime

from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.models import ReminderModel, TaskModel
from keyboards.keyboards import (
    cancel_kb, main_menu_kb,
    reminder_type_kb, reminder_tasks_kb, reminders_list_kb,
)
from states.states import ReminderStates
from utils.time_parser import format_remind_at, parse_reminder_time

logger = logging.getLogger(__name__)
router = Router()


# ── Scheduler callback (called by APScheduler, not aiogram) ───────────────────

async def _job_send_reminder(bot: Bot, user_id: int,
                              reminder_id: int, text: str) -> None:
    try:
        await bot.send_message(
            user_id,
            f"⏰ <b>Напоминание</b>\n\n{text}",
        )
        await ReminderModel.mark_sent(reminder_id)
    except Exception as e:
        logger.error(f"Failed to send reminder {reminder_id}: {e}")


def _schedule_reminder(scheduler: AsyncIOScheduler, bot: Bot,
                        reminder_id: int, user_id: int,
                        text: str, run_date: datetime) -> None:
    scheduler.add_job(
        _job_send_reminder,
        trigger="date",
        run_date=run_date,
        kwargs={"bot": bot, "user_id": user_id,
                "reminder_id": reminder_id, "text": text},
        id=f"reminder_{reminder_id}",
        replace_existing=True,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

@router.message(Command("remind"))
@router.message(F.text == "⏰ Напоминания")
async def cmd_reminders(message: Message, state: FSMContext) -> None:
    reminders = await ReminderModel.get_pending_for_user(message.from_user.id)  # type: ignore[union-attr]

    if reminders:
        lines = "\n".join(
            f"• {r['text'][:35]} — {r['remind_at'][11:16]}" for r in reminders
        )
        await message.answer(
            f"⏰ <b>Активные напоминания:</b>\n\n{lines}\n\n"
            f"Нажми на напоминание, чтобы удалить его:",
            reply_markup=reminders_list_kb(reminders),
        )
    else:
        await message.answer(
            "⏰ <b>Напоминания</b>\n\nАктивных напоминаний нет.\n\nСоздать новое?",
            reply_markup=reminder_type_kb(),
        )
    await state.set_state(ReminderStates.choosing_type)


# ── Add from list screen ──────────────────────────────────────────────────────

@router.callback_query(F.data == "remind_add")
async def remind_add_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(  # type: ignore[union-attr]
        "Выбери тип напоминания:",
        reply_markup=reminder_type_kb(),
    )
    await state.set_state(ReminderStates.choosing_type)
    await callback.answer()


# ── Delete reminder ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("remind_del:"))
async def remind_delete_cb(callback: CallbackQuery,
                            scheduler: AsyncIOScheduler) -> None:
    reminder_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    user_id = callback.from_user.id

    await ReminderModel.delete(reminder_id, user_id)

    # Cancel scheduled job if still pending
    try:
        scheduler.remove_job(f"reminder_{reminder_id}")
    except Exception:
        pass

    await callback.answer("🗑 Напоминание удалено.")

    reminders = await ReminderModel.get_pending_for_user(user_id)
    if reminders:
        await callback.message.edit_reply_markup(  # type: ignore[union-attr]
            reply_markup=reminders_list_kb(reminders)
        )
    else:
        await callback.message.edit_text(  # type: ignore[union-attr]
            "⏰ <b>Напоминания</b>\n\nАктивных напоминаний нет.\n\nСоздать новое?",
            reply_markup=reminder_type_kb(),
        )


# ── Choose type ───────────────────────────────────────────────────────────────

@router.callback_query(ReminderStates.choosing_type, F.data.startswith("remind_type:"))
async def remind_type_cb(callback: CallbackQuery, state: FSMContext) -> None:
    choice = callback.data.split(":")[1]  # type: ignore[union-attr]

    if choice == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Отменено.")  # type: ignore[union-attr]
        await callback.answer()
        return

    if choice == "task":
        tasks = await TaskModel.get_today_tasks(callback.from_user.id)
        incomplete = [t for t in tasks if not t["is_done"]]
        if not incomplete:
            await callback.answer("Нет активных задач на сегодня.", show_alert=True)
            return
        await callback.message.edit_text(  # type: ignore[union-attr]
            "📌 Выбери задачу для напоминания:",
            reply_markup=reminder_tasks_kb(incomplete),
        )
        await state.set_state(ReminderStates.choosing_task)

    elif choice == "standalone":
        await state.update_data(task_id=None)
        await callback.message.delete()  # type: ignore[union-attr]
        await callback.message.answer(  # type: ignore[union-attr]
            "✍️ Введи текст напоминания:",
            reply_markup=cancel_kb(),
        )
        await state.set_state(ReminderStates.entering_text)

    await callback.answer()


# ── Choose task ───────────────────────────────────────────────────────────────

@router.callback_query(ReminderStates.choosing_task, F.data.startswith("remind_task:"))
async def remind_task_cb(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")  # type: ignore[union-attr]
    if parts[1] == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Отменено.")  # type: ignore[union-attr]
        await callback.answer()
        return

    task_id   = int(parts[1])
    task_name = ":".join(parts[2:])  # restore if title had ":"
    await state.update_data(task_id=task_id, text=task_name)

    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer(  # type: ignore[union-attr]
        f"⏰ Задача: <b>{task_name}</b>\n\n"
        f"Введи время напоминания:\n"
        f"• <code>14:30</code> — сегодня/завтра\n"
        f"• <code>08.07 09:00</code> — конкретная дата",
        reply_markup=cancel_kb(),
    )
    await state.set_state(ReminderStates.entering_time)
    await callback.answer()


# ── Enter text (standalone) ───────────────────────────────────────────────────

@router.message(ReminderStates.entering_text, F.text == "❌ Отмена")
async def cancel_reminder(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=main_menu_kb())


@router.message(ReminderStates.entering_text)
async def process_remind_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("⚠️ Слишком коротко. Введи текст напоминания:")
        return
    if len(text) > 200:
        await message.answer("⚠️ Макс. 200 символов. Попробуй ещё раз:")
        return

    await state.update_data(text=text)
    await state.set_state(ReminderStates.entering_time)
    await message.answer(
        f"⏰ Когда напомнить?\n\n"
        f"• <code>14:30</code> — сегодня/завтра\n"
        f"• <code>08.07 09:00</code> — конкретная дата",
        reply_markup=cancel_kb(),
    )


# ── Enter time ────────────────────────────────────────────────────────────────

@router.message(ReminderStates.entering_time, F.text == "❌ Отмена")
async def cancel_reminder_time(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=main_menu_kb())


@router.message(ReminderStates.entering_time)
async def process_remind_time(message: Message, state: FSMContext,
                               scheduler: AsyncIOScheduler, bot: Bot) -> None:
    remind_at = parse_reminder_time(message.text or "")
    if not remind_at:
        await message.answer(
            "⚠️ Не могу распознать время. Попробуй:\n"
            "• <code>14:30</code>\n"
            "• <code>08.07 09:00</code>",
        )
        return

    data      = await state.get_data()
    text      = data["text"]
    task_id   = data.get("task_id")

    reminder_id = await ReminderModel.create(
        user_id=message.from_user.id,   # type: ignore[union-attr]
        text=text,
        remind_at=remind_at.strftime("%Y-%m-%d %H:%M:%S"),
        task_id=task_id,
    )
    _schedule_reminder(
        scheduler, bot, reminder_id,
        message.from_user.id, text, remind_at,  # type: ignore[union-attr]
    )
    await state.clear()
    await message.answer(
        f"✅ Напоминание установлено!\n\n"
        f"📝 <b>{text}</b>\n"
        f"🕐 {format_remind_at(remind_at)}",
        reply_markup=main_menu_kb(),
    )
