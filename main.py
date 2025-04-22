import logging
import logging.config
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, List

# Локальные импорты
from config import config
from database import db
from keyboards import (
    get_admin_keyboard,
    get_event_management_keyboard,
    get_edit_keyboard,
    get_back_keyboard
)
from utils import (
    validate_date,
    format_event,
    publish_to_channel,
    notify_organizer
)

storage = RedisStorage.from_url(config.redis_url)

# Настройка логирования
logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=config.bot_token)
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from redis.asyncio import ConnectionPool

redis_pool = ConnectionPool.from_url(
    f"redis://{config.redis_host}:{config.redis_port}/{config.redis_db}"
)
storage = RedisStorage(redis_pool, key_builder=DefaultKeyBuilder(with_bot_id=True))

dp = Dispatcher(bot, storage=storage)

class EventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_date = State()
    waiting_for_address = State()
    waiting_for_price = State()
    waiting_for_link = State()
    waiting_for_photo = State()

class AdminStates(StatesGroup):
    editing_event = State()
    editing_field = State()
    editing_value = State()
    scheduling_post = State()
    scheduling_time = State()
    sending_notification = State()
    setting_notification_frequency = State()

# ====================== ОБРАБОТЧИКИ КОМАНД ======================

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    db.save_user(user_id, {
        "username": username,
        "full_name": full_name,
        "last_active": datetime.now().isoformat(),
        "last_notified": None
    })
    
    if user_id in config.ADMIN_IDS:
        await message.answer(
            "👋 Добро пожаловать, администратор!",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            "👋 Добро пожаловать! Чтобы создать мероприятие, нажмите /create_event"
        )

@dp.message_handler(commands=['create_event'])
async def cmd_create_event(message: types.Message):
    """Обработчик команды создания мероприятия"""
    if message.from_user.id in config.ADMIN_IDS:
        await message.answer("Администраторы не могут создавать мероприятия.")
        return
    
    await EventStates.waiting_for_title.set()
    await message.answer("Введите название мероприятия:")

# ====================== ОБРАБОТЧИКИ СОЗДАНИЯ МЕРОПРИЯТИЯ ======================

@dp.message_handler(state=EventStates.waiting_for_title)
async def process_title(message: types.Message, state: FSMContext):
    """Обработчик названия мероприятия"""
    async with state.proxy() as data:
        data['title'] = message.text
        data['organizer'] = message.from_user.username
        data['organizer_id'] = message.from_user.id
    
    await EventStates.next()
    await message.answer("Введите описание мероприятия:")

@dp.message_handler(state=EventStates.waiting_for_description)
async def process_description(message: types.Message, state: FSMContext):
    """Обработчик описания мероприятия"""
    async with state.proxy() as data:
        data['description'] = message.text
    
    await EventStates.next()
    await message.answer("Введите дату и время мероприятия в формате ДД.ММ.ГГГГ ЧЧ:ММ:")

@dp.message_handler(state=EventStates.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext):
    """Обработчик даты мероприятия"""
    date = validate_date(message.text)
    if not date:
        await message.answer("Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ ЧЧ:ММ:")
        return
    
    async with state.proxy() as data:
        data['date'] = message.text
        data['date_obj'] = date.isoformat()
    
    await EventStates.next()
    await message.answer("Введите адрес мероприятия:")

@dp.message_handler(state=EventStates.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    """Обработчик адреса мероприятия"""
    async with state.proxy() as data:
        data['address'] = message.text
    
    await EventStates.next()
    await message.answer("Введите стоимость мероприятия (0 если бесплатно):")

@dp.message_handler(state=EventStates.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    """Обработчик стоимости мероприятия"""
    try:
        price = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число:")
        return
    
    async with state.proxy() as data:
        data['price'] = price
    
    await EventStates.next()
    await message.answer("Введите ссылку на мероприятие (или '-' если нет ссылки):")

@dp.message_handler(state=EventStates.waiting_for_link)
async def process_link(message: types.Message, state: FSMContext):
    """Обработчик ссылки на мероприятие"""
    async with state.proxy() as data:
        data['link'] = message.text
    
    await EventStates.next()
    await message.answer("Отправьте фото мероприятия (или любой символ если фото нет):")

@dp.message_handler(content_types=['photo', 'text'], state=EventStates.waiting_for_photo)
async def process_photo(message: types.Message, state: FSMContext):
    """Обработчик фото мероприятия"""
    async with state.proxy() as data:
        if message.photo:
            data['photo'] = message.photo[-1].file_id
        else:
            data['photo'] = None
        
        # Сохраняем мероприятие
        event_id = db.save_event(data.as_dict())
        
        # Отправляем администраторам
        for admin_id in config.ADMIN_IDS:
            try:
                if data['photo']:
                    await bot.send_photo(
                        chat_id=admin_id,
                        photo=data['photo'],
                        caption=format_event(data.as_dict()),
                        reply_markup=get_event_management_keyboard(event_id),
                        parse_mode='HTML'
                    )
                else:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=format_event(data.as_dict()),
                        reply_markup=get_event_management_keyboard(event_id),
                        parse_mode='HTML'
                    )
            except Exception as e:
                logger.error(f"Error sending event to admin {admin_id}: {e}")
    
    await state.finish()
    await message.answer("Спасибо! Ваше мероприятие отправлено на модерацию.")

# ====================== АДМИНИСТРАТИВНЫЕ ОБРАБОТЧИКИ ======================

@dp.callback_query_handler(lambda c: c.data.startswith('edit_'))
async def process_edit_callback(callback_query: types.CallbackQuery):
    """Обработчик кнопки редактирования"""
    event_id = callback_query.data.split('_')[1]
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "Выберите поле для редактирования:",
        reply_markup=get_edit_keyboard(event_id)
    )

@dp.callback_query_handler(lambda c: c.data.startswith('editfield_'))
async def process_edit_field_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора поля для редактирования"""
    _, event_id, field = callback_query.data.split('_')
    
    await AdminStates.editing_event.set()
    async with state.proxy() as data:
        data['event_id'] = event_id
        data['field'] = field
    
    await AdminStates.editing_value.set()
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        f"Введите новое значение для поля '{field}':"
    )

@dp.message_handler(state=AdminStates.editing_value)
async def process_editing_value(message: types.Message, state: FSMContext):
    """Обработчик нового значения для поля"""
    async with state.proxy() as data:
        event_id = data['event_id']
        field = data['field']
        event = db.get_event(event_id)
        
        if field == 'дата':
            new_date = validate_date(message.text)
            if not new_date:
                await message.answer("Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ ЧЧ:ММ:")
                return
            event['date'] = message.text
            event['date_obj'] = new_date.isoformat()
        elif field == 'стоимость':
            try:
                event['price'] = int(message.text)
            except ValueError:
                await message.answer("Пожалуйста, введите число:")
                return
        elif field == 'фото':
            if message.photo:
                event['photo'] = message.photo[-1].file_id
            else:
                event['photo'] = None
        else:
            event[field] = message.text
        
        db.update_event(event_id, event)
        
        if event['photo']:
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=event['photo'],
                caption=format_event(event),
                reply_markup=get_event_management_keyboard(event_id),
                parse_mode='HTML'
            )
        else:
            await bot.send_message(
                chat_id=message.from_user.id,
                text=format_event(event),
                reply_markup=get_event_management_keyboard(event_id),
                parse_mode='HTML'
            )
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('schedule_'))
async def process_schedule_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик отложенной публикации"""
    event_id = callback_query.data.split('_')[1]
    
    await AdminStates.scheduling_post.set()
    async with state.proxy() as data:
        data['event_id'] = event_id
    
    await AdminStates.scheduling_time.set()
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "Введите дату и время публикации в формате ДД.ММ.ГГГГ ЧЧ:ММ:"
    )

@dp.message_handler(state=AdminStates.scheduling_time)
async def process_scheduling_time(message: types.Message, state: FSMContext):
    """Обработчик времени публикации"""
    publish_time = validate_date(message.text)
    if not publish_time:
        await message.answer("Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ ЧЧ:ММ:")
        return
    
    async with state.proxy() as data:
        event_id = data['event_id']
        event = db.get_event(event_id)
        
        from tasks import schedule_post
        schedule_post.apply_async(
            args=[event_id, event],
            eta=publish_time
        )
        
        await message.answer(f"Мероприятие запланировано к публикации на {message.text}")
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('publish_'))
async def process_publish_callback(callback_query: types.CallbackQuery):
    """Обработчик публикации мероприятия"""
    event_id = callback_query.data.split('_')[1]
    event = db.get_event(event_id)
    
    success = await publish_to_channel(event_id, event)
    if success:
        db.move_event(event_id, "pending_events", "published_events")
        await notify_organizer(
            event['organizer_id'],
            "✅ Ваше мероприятие было опубликовано!"
        )
        await bot.answer_callback_query(callback_query.id, "Мероприятие опубликовано!")
    else:
        await bot.answer_callback_query(callback_query.id, "Ошибка публикации!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith('reject_'))
async def process_reject_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик отклонения мероприятия"""
    event_id = callback_query.data.split('_')[1]
    
    await AdminStates.editing_event.set()
    async with state.proxy() as data:
        data['event_id'] = event_id
    
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "Введите причину отклонения мероприятия:",
        reply_markup=get_back_keyboard(event_id)
    )

@dp.message_handler(state=AdminStates.editing_event)
async def process_rejection_reason(message: types.Message, state: FSMContext):
    """Обработчик причины отклонения"""
    async with state.proxy() as data:
        event_id = data['event_id']
        event = db.get_event(event_id)
        
        db.move_event(event_id, "pending_events", "rejected_events")
        await notify_organizer(
            event['organizer_id'],
            f"❌ Ваше мероприятие было отклонено. Причина: {message.text}"
        )
    
    await state.finish()
    await message.answer("Мероприятие отклонено, организатор уведомлен.")

# ====================== РАССЫЛКА УВЕДОМЛЕНИЙ ======================

@dp.message_handler(lambda message: message.from_user.id in config.ADMIN_IDS and message.text == "⚙ Настройки рассылки")
async def cmd_notification_settings(message: types.Message):
    """Обработчик настроек рассылки"""
    await AdminStates.sending_notification.set()
    await message.answer("Введите сообщение для рассылки организаторам:")

@dp.message_handler(state=AdminStates.sending_notification)
async def process_notification_message(message: types.Message, state: FSMContext):
    """Обработчик сообщения для рассылки"""
    async with state.proxy() as data:
        data['message'] = message.text
    
    await AdminStates.next()
    await message.answer("Введите частоту рассылки в днях (например, 7 для еженедельной рассылки):")

@dp.message_handler(state=AdminStates.setting_notification_frequency)
async def process_notification_frequency(message: types.Message, state: FSMContext):
    """Обработчик частоты рассылки"""
    try:
        frequency = int(message.text)
        if frequency <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите положительное число:")
        return
    
    async with state.proxy() as data:
        notification_message = data['message']
        inactive_users = db.get_inactive_organizers(frequency)
        
        for user_id in inactive_users:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=notification_message
                )
                db.update_user(user_id, {"last_notified": datetime.now().isoformat()})
            except Exception as e:
                logger.error(f"Error sending notification to {user_id}: {e}")
        
        await message.answer(
            f"Рассылка выполнена. Сообщение отправлено {len(inactive_users)} организаторам. "
            f"Следующая рассылка через {frequency} дней."
        )
    
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
