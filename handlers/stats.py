from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from database.models import TaskModel
from keyboards.keyboards import main_menu_kb

router = Router()


def _progress_bar(done: int, total: int) -> str:
    if total == 0:
        return "░" * 10
    filled = round(done / total * 10)
    return "▓" * filled + "░" * (10 - filled)


@router.message(Command("stats"))
@router.message(F.text == "📊 Статистика")
async def cmd_stats(message: Message) -> None:
    s = await TaskModel.get_stats(user_id=message.from_user.id)  # type: ignore[union-attr]

    total_today: int = s["total_today"]
    done_today:  int = s["done_today"]
    total_all:   int = s["total_all"]
    done_all:    int = s["done_all"]
    best_day:    str | None = s["best_day"]
    best_count:  int = s["best_day_count"]

    # Today block
    bar = _progress_bar(done_today, total_today)
    pct_today = f"{round(done_today / total_today * 100)}%" if total_today else "—"

    # All-time rate
    rate_all = f"{round(done_all / total_all * 100)}%" if total_all else "—"

    # Best day
    best_text = f"{best_day} ({best_count} задач)" if best_day else "пока нет"

    # Motivational footer
    pct_value = done_today / total_today if total_today else 0
    if total_today == 0:
        footer = "💡 <i>Добавь первую задачу на сегодня и начни продуктивный день!</i>"
    elif done_today == total_today:
        footer = "🎉 <i>Все задачи выполнены! Ты сегодня в ударе!</i>"
    elif pct_value >= 0.7:
        footer = "💪 <i>Отличный прогресс! Ещё совсем чуть-чуть!</i>"
    elif pct_value >= 0.3:
        footer = "🚀 <i>Хороший темп — продолжай в том же духе!</i>"
    else:
        footer = "⚡ <i>Ещё есть время сделать многое — вперёд!</i>"

    await message.answer(
        f"📊 <b>Статистика продуктивности</b>\n\n"
        f"<b>📅 Сегодня:</b>\n"
        f"[{bar}] {done_today}/{total_today} ({pct_today})\n\n"
        f"<b>📈 За всё время:</b>\n"
        f"Всего задач:           <b>{total_all}</b>\n"
        f"Выполнено:             <b>{done_all}</b>\n"
        f"Процент выполнения:    <b>{rate_all}</b>\n\n"
        f"<b>🏆 Лучший день:</b> {best_text}\n\n"
        f"{footer}",
        reply_markup=main_menu_kb(),
    )
