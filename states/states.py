from aiogram.fsm.state import State, StatesGroup


class AddTaskStates(StatesGroup):
    waiting_for_title       = State()
    waiting_for_description = State()


class ReminderStates(StatesGroup):
    choosing_type  = State()   # task-linked or standalone
    choosing_task  = State()   # pick task from inline list
    entering_text  = State()   # standalone reminder text
    entering_time  = State()   # "HH:MM" or "DD.MM HH:MM"


class FocusStates(StatesGroup):
    choosing_type      = State()   # pomodoro or custom
    entering_work_min  = State()   # custom: work duration
    entering_break_min = State()   # custom: break duration


class HabitStates(StatesGroup):
    entering_name  = State()
    choosing_emoji = State()