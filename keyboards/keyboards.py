from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить задачу"), KeyboardButton(text="📋 Мои задачи")],
            [KeyboardButton(text="📊 Статистика"),      KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def skip_or_cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ Пропустить")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


def tasks_list_kb(tasks: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for task in tasks:
        task_id = task["id"]
        is_done = task["is_done"]
        label = f"{'✅' if is_done else '⬜'} {task['title'][:35]}"
        if is_done:
            builder.button(text=label, callback_data=f"task_already_done:{task_id}")
        else:
            builder.button(text=label, callback_data=f"task_menu:{task_id}")
    builder.adjust(1)
    return builder.as_markup()


def task_action_kb(task_id: int, is_done: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_done:
        builder.button(text="✅ Отметить выполненной", callback_data=f"complete:{task_id}")
    builder.button(text="🗑 Удалить задачу",          callback_data=f"delete:{task_id}")
    builder.button(text="🔙 К списку задач",           callback_data="back_to_tasks")
    builder.adjust(1)
    return builder.as_markup()
