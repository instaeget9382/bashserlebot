import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from telegram.error import Forbidden, BadRequest
from handlers import (
    start, rules_agree, register_name, register_age, register_gender, register_city,
    register_photo, register_description, main_menu_handler, superlike_message,
    edit_photo, edit_desc, confirm_edit, confirm_delete_profile
)
from db import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен из переменной окружения или из config.py
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    try:
        from config import TOKEN
    except ImportError:
        raise ValueError("Токен бота не найден! Установите переменную окружения BOT_TOKEN или создайте config.py с токеном.")

RULES, NAME, AGE, GENDER, CITY, PHOTO, DESCRIPTION, SUPER_MESSAGE = range(8)
EDIT_PHOTO, EDIT_DESC, CONFIRM_EDIT, CONFIRM_DELETE = range(8, 12)

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, rules_agree)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_age)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_gender)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_city)],
            PHOTO: [MessageHandler(filters.PHOTO, register_photo)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_description)],
            SUPER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, superlike_message)],
            EDIT_PHOTO: [
                MessageHandler(filters.PHOTO, edit_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_photo),  # Обработка текста (ошибка)
            ],
            EDIT_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_desc),
                MessageHandler(filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.AUDIO, edit_desc),  # Обработка не-текста (ошибка)
            ],
            CONFIRM_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_edit)],
            CONFIRM_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_delete_profile)],
        },
        fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler)],
        per_message=False,
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_handler))

    async def error_handler(update: object, context):
        error = context.error
        
        # Тихая обработка ошибок, когда бот заблокирован пользователем
        if isinstance(error, Forbidden):
            logger.debug(f'Bot was blocked by user {update.effective_user.id if update and update.effective_user else "unknown"}')
            return
        
        # Тихая обработка ошибок с неверным чатом
        if isinstance(error, BadRequest) and "chat not found" in str(error).lower():
            logger.debug(f'Chat not found for update {update.update_id if update else "unknown"}')
            return
        
        # Для остальных ошибок - полное логирование
        logger.error(f'Update {update} caused error {error}', exc_info=error)

    app.add_error_handler(error_handler)

    print("Бот запущен и работает... ❤️")
    app.run_polling()

if __name__ == '__main__':
    main()