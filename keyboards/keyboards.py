from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ── Main menu ─────────────────────────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить задачу"), KeyboardButton(text="📋 Мои задачи")],
            [KeyboardButton(text="⏰ Напоминания"),      KeyboardButton(text="🎯 Фокус-режим")],
            [KeyboardButton(text="🔄 Привычки"),         KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="ℹ️ Помощь")],
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


# ── Tasks ─────────────────────────────────────────────────────────────────────

def tasks_list_kb(tasks: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for task in tasks:
        label = f"{'✅' if task['is_done'] else '⬜'} {task['title'][:35]}"
        cb    = f"task_already_done:{task['id']}" if task['is_done'] else f"task_menu:{task['id']}"
        builder.button(text=label, callback_data=cb)
    builder.adjust(1)
    return builder.as_markup()


def task_action_kb(task_id: int, is_done: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if not is_done:
        builder.button(text="✅ Отметить выполненной", callback_data=f"complete:{task_id}")
    builder.button(text="🗑 Удалить задачу",           callback_data=f"delete:{task_id}")
    builder.button(text="🔙 К списку задач",            callback_data="back_to_tasks")
    builder.adjust(1)
    return builder.as_markup()


# ── Reminders ─────────────────────────────────────────────────────────────────

def reminder_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📌 К задаче из списка",      callback_data="remind_type:task")
    builder.button(text="✍️ Отдельное напоминание",   callback_data="remind_type:standalone")
    builder.button(text="❌ Отмена",                   callback_data="remind_type:cancel")
    builder.adjust(1)
    return builder.as_markup()


def reminder_tasks_kb(tasks: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.button(
            text=f"📌 {t['title'][:40]}",
            callback_data=f"remind_task:{t['id']}:{t['title'][:30]}"
        )
    builder.button(text="❌ Отмена", callback_data="remind_task:cancel")
    builder.adjust(1)
    return builder.as_markup()


def reminders_list_kb(reminders: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for r in reminders:
        label = f"⏰ {r['text'][:30]}  ({r['remind_at'][11:16]})"
        builder.button(text=label, callback_data=f"remind_del:{r['id']}")
    builder.button(text="➕ Добавить напоминание", callback_data="remind_add")
    builder.adjust(1)
    return builder.as_markup()


# ── Focus ─────────────────────────────────────────────────────────────────────

def focus_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🍅 Помодоро  (25 / 5 мин)",  callback_data="focus_type:pomodoro")
    builder.button(text="⚙️ Свои настройки",           callback_data="focus_type:custom")
    builder.button(text="📊 Статистика сессий",        callback_data="focus_type:stats")
    builder.button(text="❌ Отмена",                    callback_data="focus_type:cancel")
    builder.adjust(1)
    return builder.as_markup()


def focus_after_work_kb(work_min: int, break_min: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Ещё одна сессия",
                   callback_data=f"focus_again:{work_min}:{break_min}")
    builder.button(text="⏹ Завершить",  callback_data="focus_stop")
    builder.adjust(1)
    return builder.as_markup()


def focus_after_break_kb(work_min: int, break_min: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Новая рабочая сессия",
                   callback_data=f"focus_again:{work_min}:{break_min}")
    builder.button(text="⏹ На сегодня всё",  callback_data="focus_stop")
    builder.adjust(1)
    return builder.as_markup()


# ── Habits ────────────────────────────────────────────────────────────────────

def habits_list_kb(habits: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for h in habits:
        mark  = "✅" if h["done_today"] else "⬜"
        label = f"{mark} {h['emoji']} {h['name'][:35]}"
        builder.button(text=label, callback_data=f"habit_menu:{h['id']}")
    builder.button(text="➕ Добавить привычку",    callback_data="habit_add")
    builder.button(text="📊 Общая статистика",     callback_data="habit_overall_stats")
    builder.adjust(1)
    return builder.as_markup()


def habit_action_kb(habit_id: int, done_today: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if done_today:
        builder.button(text="⬜ Снять отметку",      callback_data=f"habit_toggle:{habit_id}")
    else:
        builder.button(text="✅ Отметить выполненной", callback_data=f"habit_toggle:{habit_id}")
    builder.button(text="🗑 Удалить привычку",  callback_data=f"habit_delete:{habit_id}")
    builder.button(text="🔙 К привычкам",       callback_data="habits_back")
    builder.adjust(1)
    return builder.as_markup()


HABIT_EMOJIS = ["📚", "💧", "🏋️", "🧘", "🍎", "😴", "💊", "✍️",
                "🎯", "🚶", "💻", "🎵", "🌿", "🏃", "🥗", "🧹"]

def habit_emoji_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for emoji in HABIT_EMOJIS:
        builder.button(text=emoji, callback_data=f"habit_emoji:{emoji}")
    builder.button(text="⏭ Пропустить (⭐)", callback_data="habit_emoji:⭐")
    builder.adjust(4)
    return builder.as_markup()