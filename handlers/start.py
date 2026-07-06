from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from database.models import UserModel
from keyboards.keyboards import main_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await UserModel.get_or_create(
        user_id=message.from_user.id,          # type: ignore[union-attr]
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
        f"✅ Отмечать выполненные задачи\n"
        f"📊 Показывать статистику продуктивности\n\n"
        f"Начнём? Выбери действие в меню ниже 👇",
        reply_markup=main_menu_kb(),
    )


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 <b>Помощь по DayFlowBot</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — Главное меню\n"
        "/help  — Эта справка\n"
        "/add   — Добавить задачу\n"
        "/tasks — Список задач на сегодня\n"
        "/stats — Статистика продуктивности\n\n"
        "<b>Кнопки меню:</b>\n"
        "➕ <b>Добавить задачу</b> — создать новое дело\n"
        "📋 <b>Мои задачи</b>     — список дел на сегодня\n"
        "📊 <b>Статистика</b>     — твой прогресс\n\n"
        "💡 <i>Скоро: напоминания, фокус-режим и трекер привычек!</i>",
        reply_markup=main_menu_kb(),
    )
