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

# Определим состояния разговора
EMAIL, MESSAGE, FILE = range(3)

# Функция для обработки команды /start
def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    update.message.reply_text('Привет! Пожалуйста, отправь мне свой email.')
    return EMAIL

# Функция для обработки полученного email
def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text
    context.user_data['email'] = email
    update.message.reply_text(f'Спасибо! Теперь напиши мне своё сообщение.')
    return MESSAGE

# Функция для обработки сообщения
def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    context.user_data['message'] = message
    update.message.reply_text(f'Теперь прикрепи файл (картинку или PDF). Он должен быть меньше 2 МБ.')
    return FILE

# Функция для обработки прикрепленного файла
def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = update.message.document or update.message.photo[-1]
    file_size = file.file_size

    if file_size > 2 * 1024 * 1024:
        update.message.reply_text('Файл слишком большой. Пожалуйста, отправь файл размером меньше 2 МБ.')
        return FILE

    file_extension = file.file_name.split('.')[-1].lower()
    if file_extension not in ['jpg', 'jpeg', 'png', 'pdf']:
        update.message.reply_text('Неверный формат файла. Пожалуйста, отправь картинку или PDF.')
        return FILE

    context.user_data['file'] = file
    update.message.reply_text('Файл получен!')
    return ConversationHandler.END

# Функция для выхода из разговора
def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    update.message.reply_text('До свидания!')
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