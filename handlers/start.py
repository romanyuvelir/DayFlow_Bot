from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from database.models import UserModel
from keyboards.keyboards import main_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await UserModel.get_or_create(
        user_id=message.from_user.id,           # type: ignore[union-attr]
        username=message.from_user.username or "",  # type: ignore[union-attr]
        first_name=message.from_user.first_name or "",  # type: ignore[union-attr]
    )
    name = message.from_user.first_name or "друг"  # type: ignore[union-attr]
    await message.answer(
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"Я <b>DayFlowBot</b> — твой личный помощник по задачам и продуктивности.\n\n"
        f"<b>Что я умею:</b>\n"
        f"➕ Добавлять задачи на день\n"
        f"📋 Показывать список дел\n"
        f"⏰ Напоминать в нужное время\n"
        f"🎯 Помогать фокусироваться (Помодоро)\n"
        f"🔄 Отслеживать привычки и стрики\n"
        f"📊 Показывать статистику продуктивности\n\n"
        f"Выбери действие в меню 👇",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 <b>Помощь по DayFlowBot</b>\n\n"
        "<b>Команды:</b>\n"
        "/start   — Главное меню\n"
        "/add     — Добавить задачу\n"
        "/tasks   — Задачи на сегодня\n"
        "/remind  — Напоминания\n"
        "/focus   — Фокус-режим\n"
        "/habits  — Трекер привычек\n"
        "/stats   — Статистика\n\n"
        "<b>Кнопки меню:</b>\n"
        "➕ <b>Добавить задачу</b> — создать дело на сегодня\n"
        "📋 <b>Мои задачи</b>     — список и управление\n"
        "⏰ <b>Напоминания</b>    — к задаче или отдельное\n"
        "🎯 <b>Фокус-режим</b>    — Помодоро или своё время\n"
        "🔄 <b>Привычки</b>       — стрики и статистика\n"
        "📊 <b>Статистика</b>     — твой прогресс",
        reply_markup=main_menu_kb(),
    )