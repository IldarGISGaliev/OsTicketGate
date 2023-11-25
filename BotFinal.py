import logging
import configparser
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Определим состояния разговора
EMAIL, MESSAGE, FILE = range(3)

# Функция для обработки команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
   await update.message.reply_text('Привет! Пожалуйста, отправь мне свой email.')
   return EMAIL

# Функция для обработки полученного email
async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text
    context.user_data['email'] = email
    await update.message.reply_text(f'Спасибо! Теперь напиши мне своё сообщение.')
    return MESSAGE

# Функция для обработки сообщения
async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    context.user_data['message'] = message
    await update.message.reply_text(f'Теперь прикрепи файл (картинку или PDF). Он должен быть меньше 2 МБ.')
    return FILE

# Функция для обработки прикрепленного файла
async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = update.message.document or update.message.photo[-1]
    file_size = file.file_size

    if file_size > 2 * 1024 * 1024:
        await update.message.reply_text('Файл слишком большой. Пожалуйста, отправь файл размером меньше 2 МБ.')
        return FILE

    file_extension = file.file_name.split('.')[-1].lower()
    if file_extension not in ['jpg', 'jpeg', 'png', 'pdf']:
        await update.message.reply_text('Неверный формат файла. Пожалуйста, отправь картинку или PDF.')
        return FILE

    context.user_data['file'] = file
    await update.message.reply_text('Файл получен!')
    return ConversationHandler.END

# Функция для выхода из разговора
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('До свидания!')
    return ConversationHandler.END

def main():
    # Создание Updater и передача ему токена вашего бота
    config = configparser.ConfigParser()
    config.read('secrets.ini')
    secret_token = config['telegram']['token']
    application = Application.builder().token(secret_token).build()



    # Определение обработчика разговоров
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.Command(), get_email)],
            MESSAGE: [MessageHandler(filters.TEXT & ~filters.Command(), get_message)],
            FILE: [MessageHandler(filters.ATTACHMENT | filters.PHOTO, get_file)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)

    # Начало поиска обновлений
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()