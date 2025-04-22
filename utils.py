from config import config
from aiogram import Bot
from datetime import datetime
import pytz

def validate_date(date_str):
    """Проверка формата даты"""
    try:
        return datetime.strptime(date_str, '%d.%m.%Y %H:%M').replace(
            tzinfo=pytz.timezone(config.timezone)
        )
    except ValueError:
        return None

def format_event(event):
    """Форматирование мероприятия в текст"""
    return (
        f"📌 <b>{event['title']}</b>\n\n"
        f"📝 <i>{event['description']}</i>\n\n"
        f"📅 <b>Дата:</b> {event['date']}\n"
        f"📍 <b>Адрес:</b> {event['address']}\n"
        f"💰 <b>Стоимость:</b> {event['price']} руб.\n"
        f"🔗 <b>Ссылка:</b> {event['link']}\n\n"
        f"Организатор: @{event['organizer']}"
    )

async def publish_to_channel(event_id, event):
    """Публикация мероприятия в канал"""
    try:
        bot = Bot(token=config.bot_token)
        if event.get('photo'):
            await bot.send_photo(
                chat_id=config.channel_id,
                photo=event['photo'],
                caption=format_event(event),
                parse_mode='HTML'
            )
        else:
            await bot.send_message(
                chat_id=config.channel_id,
                text=format_event(event),
                parse_mode='HTML'
            )
        return True
    except Exception as e:
        print(f"Ошибка публикации: {e}")
        return False
    finally:
        await bot.close()

async def notify_organizer(organizer_id, message):
    """Уведомление организатора"""
    try:
        bot = Bot(token=config.bot_token)
        await bot.send_message(
            chat_id=organizer_id,
            text=message
        )
        return True
    except Exception as e:
        print(f"Ошибка уведомления организатора: {e}")
        return False
    finally:
        await bot.close()