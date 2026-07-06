import logging
from datetime import datetime, timedelta

from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.models import FocusModel
from keyboards.keyboards import (
    cancel_kb, focus_type_kb, focus_after_work_kb, focus_after_break_kb, main_menu_kb,
)
from states.states import FocusStates

logger = logging.getLogger(__name__)
router = Router()

POMODORO_WORK  = 25
POMODORO_BREAK = 5


# ── Scheduler callbacks ───────────────────────────────────────────────────────

async def _job_work_end(bot: Bot, user_id: int,
                         session_id: int, break_minutes: int,
                         work_minutes: int, scheduler: AsyncIOScheduler) -> None:
    try:
        await bot.send_message(
            user_id,
            f"⏸ <b>Рабочая сессия завершена!</b>\n\n"
            f"Отличная работа 💪 Время на перерыв — <b>{break_minutes} мин</b>.\n\n"
            f"Отдыхай, я напомню когда пора вернуться.",
        )
        # Schedule break end
        scheduler.add_job(
            _job_break_end,
            trigger="date",
            run_date=datetime.now() + timedelta(minutes=break_minutes),
            kwargs={
                "bot": bot, "user_id": user_id, "session_id": session_id,
                "work_minutes": work_minutes, "break_minutes": break_minutes,
            },
            id=f"focus_break_{user_id}",
            replace_existing=True,
        )
    except Exception as e:
        logger.error(f"focus work_end error: {e}")


async def _job_break_end(bot: Bot, user_id: int, session_id: int,
                          work_minutes: int, break_minutes: int) -> None:
    try:
        await FocusModel.complete_session(session_id)
        await bot.send_message(
            user_id,
            f"✅ <b>Перерыв закончен!</b>\n\n"
            f"Готов к следующей сессии? 🚀",
            reply_markup=focus_after_break_kb(work_minutes, break_minutes),
        )
    except Exception as e:
        logger.error(f"focus break_end error: {e}")


def _start_focus(scheduler: AsyncIOScheduler, bot: Bot,
                  user_id: int, session_id: int,
                  work_min: int, break_min: int) -> None:
    # Cancel any existing focus jobs for this user
    for job_id in (f"focus_work_{user_id}", f"focus_break_{user_id}"):
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass

    scheduler.add_job(
        _job_work_end,
        trigger="date",
        run_date=datetime.now() + timedelta(minutes=work_min),
        kwargs={
            "bot": bot, "user_id": user_id, "session_id": session_id,
            "break_minutes": break_min, "work_minutes": work_min,
            "scheduler": scheduler,
        },
        id=f"focus_work_{user_id}",
        replace_existing=True,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

@router.message(Command("focus"))
@router.message(F.text == "🎯 Фокус-режим")
async def cmd_focus(message: Message, state: FSMContext) -> None:
    await state.set_state(FocusStates.choosing_type)
    await message.answer(
        "🎯 <b>Фокус-режим</b>\n\n"
        "Выбери формат сессии:",
        reply_markup=focus_type_kb(),
    )


# ── Choose type ───────────────────────────────────────────────────────────────

@router.callback_query(FocusStates.choosing_type, F.data.startswith("focus_type:"))
async def focus_type_cb(callback: CallbackQuery, state: FSMContext,
                         scheduler: AsyncIOScheduler, bot: Bot) -> None:
    choice = callback.data.split(":")[1]  # type: ignore[union-attr]
    user_id = callback.from_user.id

    if choice == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Отменено.")  # type: ignore[union-attr]
        await callback.answer()
        return

    if choice == "stats":
        s = await FocusModel.get_stats(user_id)
        text = (
            f"📊 <b>Статистика фокус-сессий</b>\n\n"
            f"<b>Сегодня:</b>\n"
            f"Сессий: <b>{s['today_sessions']}</b>  |  "
            f"Времени: <b>{s['today_minutes']} мин</b>\n\n"
            f"<b>За всё время:</b>\n"
            f"Всего сессий:     <b>{s['total']}</b>\n"
            f"Завершено:        <b>{s['completed']}</b>\n"
            f"Суммарно в фокусе: <b>{s['total_minutes']} мин "
            f"({s['total_minutes'] // 60} ч {s['total_minutes'] % 60} мин)</b>"
        )
        await callback.message.edit_text(text, reply_markup=focus_type_kb())  # type: ignore[union-attr]
        await callback.answer()
        return

    if choice == "pomodoro":
        work_min, break_min = POMODORO_WORK, POMODORO_BREAK
        session_id = await FocusModel.create_session(user_id, work_min, break_min, "pomodoro")
        _start_focus(scheduler, bot, user_id, session_id, work_min, break_min)
        await state.clear()
        await callback.message.edit_text(  # type: ignore[union-attr]
            f"🍅 <b>Помодоро запущен!</b>\n\n"
            f"⏱ Рабочая сессия: <b>{work_min} мин</b>\n"
            f"☕ Перерыв: <b>{break_min} мин</b>\n\n"
            f"Сосредоточься, я напомню когда время выйдет. Удачи! 💪",
        )

    elif choice == "custom":
        await state.set_state(FocusStates.entering_work_min)
        await callback.message.delete()  # type: ignore[union-attr]
        await callback.message.answer(  # type: ignore[union-attr]
            "⚙️ <b>Кастомный фокус</b>\n\nСколько минут рабочая сессия?",
            reply_markup=cancel_kb(),
        )

    await callback.answer()


# ── Custom: enter work minutes ────────────────────────────────────────────────

@router.message(FocusStates.entering_work_min, F.text == "❌ Отмена")
@router.message(FocusStates.entering_break_min, F.text == "❌ Отмена")
async def cancel_focus(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=main_menu_kb())


@router.message(FocusStates.entering_work_min)
async def process_work_min(message: Message, state: FSMContext) -> None:
    try:
        minutes = int((message.text or "").strip())
        if not (1 <= minutes <= 180):
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введи число от 1 до 180:")
        return

    await state.update_data(work_min=minutes)
    await state.set_state(FocusStates.entering_break_min)
    await message.answer(
        f"✅ Рабочая сессия: <b>{minutes} мин</b>\n\nСколько минут перерыв?",
        reply_markup=cancel_kb(),
    )


@router.message(FocusStates.entering_break_min)
async def process_break_min(message: Message, state: FSMContext,
                              scheduler: AsyncIOScheduler, bot: Bot) -> None:
    try:
        break_min = int((message.text or "").strip())
        if not (1 <= break_min <= 60):
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Введи число от 1 до 60:")
        return

    data     = await state.get_data()
    work_min = data["work_min"]
    user_id  = message.from_user.id  # type: ignore[union-attr]

    session_id = await FocusModel.create_session(user_id, work_min, break_min, "custom")
    _start_focus(scheduler, bot, user_id, session_id, work_min, break_min)
    await state.clear()
    await message.answer(
        f"🎯 <b>Фокус-сессия запущена!</b>\n\n"
        f"⏱ Работа: <b>{work_min} мин</b>\n"
        f"☕ Перерыв: <b>{break_min} мин</b>\n\n"
        f"Сосредоточься, я напомню! 💪",
        reply_markup=main_menu_kb(),
    )


# ── Repeat session callback ───────────────────────────────────────────────────

@router.callback_query(F.data.startswith("focus_again:"))
async def focus_again_cb(callback: CallbackQuery,
                          scheduler: AsyncIOScheduler, bot: Bot) -> None:
    parts     = callback.data.split(":")  # type: ignore[union-attr]
    work_min  = int(parts[1])
    break_min = int(parts[2])
    user_id   = callback.from_user.id

    session_id = await FocusModel.create_session(
        user_id, work_min, break_min,
        "pomodoro" if work_min == POMODORO_WORK and break_min == POMODORO_BREAK else "custom",
    )
    _start_focus(scheduler, bot, user_id, session_id, work_min, break_min)
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"🚀 <b>Новая сессия запущена!</b>\n\n"
        f"⏱ Работа: <b>{work_min} мин</b>  |  ☕ Перерыв: <b>{break_min} мин</b>\n\n"
        f"Вперёд! 💪",
    )
    await callback.answer()


@router.callback_query(F.data == "focus_stop")
async def focus_stop_cb(callback: CallbackQuery,
                         scheduler: AsyncIOScheduler) -> None:
    user_id = callback.from_user.id
    for job_id in (f"focus_work_{user_id}", f"focus_break_{user_id}"):
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
    await callback.message.edit_text(  # type: ignore[union-attr]
        "⏹ Фокус-режим остановлен. Хорошая работа сегодня! 🎉"
    )
    await callback.answer()
