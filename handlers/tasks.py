from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.models import TaskModel
from keyboards.keyboards import (
    cancel_kb,
    main_menu_kb,
    skip_or_cancel_kb,
    task_action_kb,
    tasks_list_kb,
)
from states.states import AddTaskStates

router = Router()

# ── helpers ──────────────────────────────────────────────────────────────────

def _progress_bar(done: int, total: int) -> str:
    if total == 0:
        return "░" * 10
    filled = round(done / total * 10)
    return "▓" * filled + "░" * (10 - filled)


async def _send_task_list(target: Message | CallbackQuery, user_id: int) -> None:
    tasks = await TaskModel.get_today_tasks(user_id=user_id)
    done = sum(1 for t in tasks if t["is_done"])
    total = len(tasks)
    bar = _progress_bar(done, total)

    text = (
        f"📋 <b>Задачи на сегодня</b>\n\n"
        f"[{bar}] {done}/{total}\n\n"
        f"Нажми на задачу для управления:"
    )

    if isinstance(target, Message):
        if not tasks:
            await target.answer(
                "📋 <b>Задачи на сегодня</b>\n\nСписок пуст. Добавь первую задачу! 🚀",
                reply_markup=main_menu_kb(),
            )
            return
        await target.answer(text, reply_markup=tasks_list_kb(tasks))
    else:  # CallbackQuery
        if not tasks:
            await target.message.edit_text(  # type: ignore[union-attr]
                "📋 <b>Задачи на сегодня</b>\n\nСписок пуст. Добавь первую задачу! 🚀"
            )
            return
        await target.message.edit_text(  # type: ignore[union-attr]
            text, reply_markup=tasks_list_kb(tasks)
        )


# ── add task FSM ──────────────────────────────────────────────────────────────

@router.message(Command("add"))
@router.message(F.text == "➕ Добавить задачу")
async def cmd_add_task(message: Message, state: FSMContext) -> None:
    await state.set_state(AddTaskStates.waiting_for_title)
    await message.answer(
        "📝 <b>Новая задача</b>\n\nВведи название задачи:",
        reply_markup=cancel_kb(),
    )


@router.message(AddTaskStates.waiting_for_title, F.text == "❌ Отмена")
@router.message(AddTaskStates.waiting_for_description, F.text == "❌ Отмена")
async def cancel_add(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Добавление отменено.", reply_markup=main_menu_kb())


@router.message(AddTaskStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if len(title) < 2:
        await message.answer("⚠️ Название слишком короткое (минимум 2 символа). Попробуй ещё раз:")
        return
    if len(title) > 100:
        await message.answer("⚠️ Слишком длинное название (макс. 100 символов). Сократи и повтори:")
        return

    await state.update_data(title=title)
    await state.set_state(AddTaskStates.waiting_for_description)
    await message.answer(
        f"✏️ Хочешь добавить описание к задаче <b>«{title}»</b>?\n\n"
        f"Введи описание или нажми <b>⏭ Пропустить</b>:",
        reply_markup=skip_or_cancel_kb(),
    )


@router.message(AddTaskStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    description: str | None = None

    if raw != "⏭ Пропустить":
        if len(raw) > 300:
            await message.answer("⚠️ Описание слишком длинное (макс. 300 символов). Попробуй ещё раз:")
            return
        description = raw

    data = await state.get_data()
    title: str = data["title"]

    await TaskModel.add_task(
        user_id=message.from_user.id,  # type: ignore[union-attr]
        title=title,
        description=description,
    )
    await state.clear()

    desc_line = f"\n📄 <i>{description}</i>" if description else ""
    await message.answer(
        f"✅ Задача добавлена!\n\n"
        f"📌 <b>{title}</b>{desc_line}\n\n"
        f"Удачи! 💪",
        reply_markup=main_menu_kb(),
    )


# ── task list ─────────────────────────────────────────────────────────────────

@router.message(Command("tasks"))
@router.message(F.text == "📋 Мои задачи")
async def cmd_tasks(message: Message) -> None:
    await _send_task_list(message, message.from_user.id)  # type: ignore[union-attr]


# ── callbacks ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("task_menu:"))
async def task_menu_cb(callback: CallbackQuery) -> None:
    task_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    task = await TaskModel.get_task_by_id(task_id, callback.from_user.id)

    if not task:
        await callback.answer("❌ Задача не найдена.", show_alert=True)
        return

    status = "✅ Выполнена" if task["is_done"] else "🔲 Активна"
    desc_line = f"\n\n📄 <i>{task['description']}</i>" if task.get("description") else ""

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"📌 <b>{task['title']}</b>\n"
        f"Статус: {status}{desc_line}",
        reply_markup=task_action_kb(task_id, bool(task["is_done"])),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task_already_done:"))
async def task_already_done_cb(callback: CallbackQuery) -> None:
    await callback.answer("✅ Эта задача уже выполнена!", show_alert=True)


@router.callback_query(F.data.startswith("complete:"))
async def complete_task_cb(callback: CallbackQuery) -> None:
    task_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    success = await TaskModel.complete_task(task_id, callback.from_user.id)

    if not success:
        await callback.answer("❌ Не удалось выполнить задачу.", show_alert=True)
        return

    await callback.answer("🎉 Отличная работа! Задача выполнена!")
    await _send_task_list(callback, callback.from_user.id)


@router.callback_query(F.data.startswith("delete:"))
async def delete_task_cb(callback: CallbackQuery) -> None:
    task_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    success = await TaskModel.delete_task(task_id, callback.from_user.id)

    if not success:
        await callback.answer("❌ Не удалось удалить задачу.", show_alert=True)
        return

    await callback.answer("🗑 Задача удалена.")
    await _send_task_list(callback, callback.from_user.id)


@router.callback_query(F.data == "back_to_tasks")
async def back_to_tasks_cb(callback: CallbackQuery) -> None:
    await _send_task_list(callback, callback.from_user.id)
    await callback.answer()
