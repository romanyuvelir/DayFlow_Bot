from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database.models import HabitModel
from keyboards.keyboards import (
    cancel_kb, habit_action_kb, habit_emoji_kb,
    habits_list_kb, main_menu_kb,
)
from states.states import HabitStates

router = Router()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _streak_emoji(streak: int) -> str:
    if streak >= 30: return "🏆"
    if streak >= 14: return "🔥"
    if streak >= 7:  return "⚡"
    if streak >= 3:  return "✨"
    return "💫"


async def _show_habits_list(target: Message | CallbackQuery, user_id: int) -> None:
    habits = await HabitModel.get_active(user_id)
    done   = sum(1 for h in habits if h["done_today"])
    total  = len(habits)

    if isinstance(target, Message):
        send = target.answer
        edit = None
    else:
        send = target.message.answer  # type: ignore[union-attr]
        edit = target.message.edit_text  # type: ignore[union-attr]

    if not habits:
        text = (
            "🔄 <b>Трекер привычек</b>\n\n"
            "Привычек пока нет. Добавь первую!"
        )
        kb = habits_list_kb([])
    else:
        bar    = "▓" * round(done / total * 10) + "░" * (10 - round(done / total * 10))
        text   = (
            f"🔄 <b>Привычки на сегодня</b>\n\n"
            f"[{bar}] {done}/{total}\n\n"
            f"Нажми, чтобы отметить или посмотреть статистику:"
        )
        kb = habits_list_kb(habits)

    if edit:
        await edit(text, reply_markup=kb)
    else:
        await send(text, reply_markup=kb)


# ── Entry point ───────────────────────────────────────────────────────────────

@router.message(Command("habits"))
@router.message(F.text == "🔄 Привычки")
async def cmd_habits(message: Message) -> None:
    await _show_habits_list(message, message.from_user.id)  # type: ignore[union-attr]


# ── Habit menu (tap habit) ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("habit_menu:"))
async def habit_menu_cb(callback: CallbackQuery) -> None:
    habit_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    user_id  = callback.from_user.id

    habit = await HabitModel.get_by_id(habit_id, user_id)
    if not habit:
        await callback.answer("❌ Привычка не найдена.", show_alert=True)
        return

    stats      = await HabitModel.get_stats(habit_id, user_id)
    done_today = stats["done_today"]
    today_str  = "✅ Выполнено" if done_today else "⬜ Не выполнено"
    s_emoji    = _streak_emoji(stats["current_streak"])

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"{habit['emoji']} <b>{habit['name']}</b>\n"
        f"Сегодня: {today_str}\n\n"
        f"{s_emoji} Текущая серия: <b>{stats['current_streak']} дн.</b>\n"
        f"🏆 Лучшая серия:  <b>{stats['best_streak']} дн.</b>\n"
        f"📊 Всего выполнено: <b>{stats['total']} раз</b>",
        reply_markup=habit_action_kb(habit_id, done_today),
    )
    await callback.answer()


# ── Toggle today ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("habit_toggle:"))
async def habit_toggle_cb(callback: CallbackQuery) -> None:
    habit_id   = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    user_id    = callback.from_user.id
    now_done   = await HabitModel.toggle_today(habit_id, user_id)

    habit = await HabitModel.get_by_id(habit_id, user_id)
    if not habit:
        await callback.answer("❌ Привычка не найдена.", show_alert=True)
        return

    stats      = await HabitModel.get_stats(habit_id, user_id)
    today_str  = "✅ Выполнено" if now_done else "⬜ Не выполнено"
    s_emoji    = _streak_emoji(stats["current_streak"])

    await callback.message.edit_text(  # type: ignore[union-attr]
        f"{habit['emoji']} <b>{habit['name']}</b>\n"
        f"Сегодня: {today_str}\n\n"
        f"{s_emoji} Текущая серия: <b>{stats['current_streak']} дн.</b>\n"
        f"🏆 Лучшая серия:  <b>{stats['best_streak']} дн.</b>\n"
        f"📊 Всего выполнено: <b>{stats['total']} раз</b>",
        reply_markup=habit_action_kb(habit_id, now_done),
    )
    msg = "✅ Отмечено!" if now_done else "⬜ Отметка снята."
    await callback.answer(msg)


# ── Delete habit ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("habit_delete:"))
async def habit_delete_cb(callback: CallbackQuery) -> None:
    habit_id = int(callback.data.split(":")[1])  # type: ignore[union-attr]
    success  = await HabitModel.delete(habit_id, callback.from_user.id)
    if not success:
        await callback.answer("❌ Не удалось удалить.", show_alert=True)
        return
    await callback.answer("🗑 Привычка удалена.")
    await _show_habits_list(callback, callback.from_user.id)


# ── Back to list ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "habits_back")
async def habits_back_cb(callback: CallbackQuery) -> None:
    await _show_habits_list(callback, callback.from_user.id)
    await callback.answer()


# ── Overall stats ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "habit_overall_stats")
async def habit_overall_stats_cb(callback: CallbackQuery) -> None:
    s = await HabitModel.get_overall_stats(callback.from_user.id)
    pct = round(s["done_today"] / s["total_habits"] * 100) if s["total_habits"] else 0
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"📊 <b>Общая статистика привычек</b>\n\n"
        f"Активных привычек:   <b>{s['total_habits']}</b>\n"
        f"Выполнено сегодня:   <b>{s['done_today']}/{s['total_habits']} ({pct}%)</b>\n\n"
        f"Активных дней:       <b>{s['active_days']}</b>\n"
        f"Всего отметок:       <b>{s['total_logs']}</b>",
        reply_markup=habits_list_kb(await HabitModel.get_active(callback.from_user.id)),
    )
    await callback.answer()


# ── Add habit FSM ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "habit_add")
async def habit_add_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(HabitStates.entering_name)
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer(  # type: ignore[union-attr]
        "🔄 <b>Новая привычка</b>\n\nВведи название:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(HabitStates.entering_name, F.text == "❌ Отмена")
async def cancel_habit(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=main_menu_kb())


@router.message(HabitStates.entering_name)
async def process_habit_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("⚠️ Название слишком короткое (мин. 2 символа):")
        return
    if len(name) > 60:
        await message.answer("⚠️ Слишком длинное (макс. 60 символов):")
        return

    await state.update_data(name=name)
    await state.set_state(HabitStates.choosing_emoji)
    await message.answer(
        f"Отлично! Выбери эмодзи для <b>«{name}»</b>:",
        reply_markup=habit_emoji_kb(),
    )


@router.callback_query(HabitStates.choosing_emoji, F.data.startswith("habit_emoji:"))
async def process_habit_emoji(callback: CallbackQuery, state: FSMContext) -> None:
    emoji    = callback.data.split(":")[1]  # type: ignore[union-attr]
    data     = await state.get_data()
    name     = data["name"]
    user_id  = callback.from_user.id

    await HabitModel.create(user_id, name, emoji)
    await state.clear()
    await callback.message.delete()  # type: ignore[union-attr]
    await callback.message.answer(  # type: ignore[union-attr]
        f"✅ Привычка добавлена!\n\n{emoji} <b>{name}</b>\n\nУдачи! 🔥",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()
