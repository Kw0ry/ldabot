from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_keyboard():
    """Клавиатура для администратора"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📋 Список мероприятий"))
    keyboard.add(KeyboardButton("⚙ Настройки рассылки"))
    return keyboard

def get_event_management_keyboard(event_id):
    """Клавиатура для управления мероприятием"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✏ Редактировать", callback_data=f"edit_{event_id}"))
    keyboard.add(InlineKeyboardButton("⏰ Отложить публикацию", callback_data=f"schedule_{event_id}"))
    keyboard.add(InlineKeyboardButton("✅ Опубликовать", callback_data=f"publish_{event_id}"))
    keyboard.add(InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{event_id}"))
    return keyboard

def get_edit_keyboard(event_id):
    """Клавиатура для выбора поля редактирования"""
    keyboard = InlineKeyboardMarkup()
    fields = ["Название", "Описание", "Дата", "Адрес", "Стоимость", "Ссылка", "Фото"]
    for field in fields:
        keyboard.add(InlineKeyboardButton(field, callback_data=f"editfield_{event_id}_{field.lower()}"))
    keyboard.add(InlineKeyboardButton("⬅ Назад", callback_data=f"back_{event_id}"))
    return keyboard

def get_back_keyboard(event_id):
    """Клавиатура с кнопкой 'Назад'"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("⬅ Назад", callback_data=f"back_{event_id}"))
    return keyboard