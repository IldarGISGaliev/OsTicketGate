import logging
import configparser
import requests
import base64
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
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
   await update.message.reply_text('Привет! Пожалуйста, отправьте мне свой email.',reply_markup=ReplyKeyboardRemove())
   return EMAIL

# Функция для обработки полученного email
async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text
    context.user_data['email'] = email
    await update.message.reply_text(f'Спасибо! С какими ограничениями вы столкнулись?')
    return MESSAGE

# Функция для обработки сообщения
async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text
    context.user_data['message'] = message
    await update.message.reply_text(f'Если есть официальный отказ прикрепи файл (картинку или PDF). Он должен быть меньше 2 МБ. Или напиши /skip')
    return FILE

# Пропускаем обработку фото
async def skip_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
     # URL и заголовки для POST запроса
    config = configparser.ConfigParser()
    config.read('secrets.ini')
    xapitoken = config['OSTicket']['xapitoken']
    url = config['OSTicket']['path']
    user = update.message.from_user
    data = {
        'alert': True,
        'autorespond': True,
    'source': 'API',
    'name': user.full_name,
    'email': context.user_data['email'],
    'phone': user.id,
    'subject': 'Ticket from TG gate',
    'ip': '123.211.233.122',
    'message': context.user_data['message']
    }
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': xapitoken
    }

    # Выполнение POST запроса
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.info("Error while creating new ticket %s ", e)
    await update.message.reply_text('Данные отправлены, проверьте почту для отслеживания обновлений!') 
    return ConversationHandler.END

# Функция для обработки прикрепленного файла
async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = update.message.document or update.message.photo[-1]
    file_size = file.file_size

    if file_size > 2 * 1024 * 1024:
        await update.message.reply_text('Файл слишком большой. Пожалуйста, отправь файл размером меньше 2 МБ.')
        return FILE
    if update.message.document is None:
        fileContent = await update.message.photo[-1].get_file()  
        DataOPrefix='data:image/png;base64,'
        DataName='Image.png'
    else:
        fileContent = await update.message.document.get_file()
        DataOPrefix='data:application/pdf;base64,'
        DataName='Doc.pdf'
    fileByteCor=await fileContent.download_as_bytearray()   
    fileByte = bytes(fileByteCor)
    file64= base64.b64encode(fileByte).decode('utf-8') 
    await update.message.reply_text('Файл получен!')
    # URL и заголовки для POST запроса
    config = configparser.ConfigParser()
    config.read('secrets.ini')
    xapitoken = config['OSTicket']['xapitoken']
    url = config['OSTicket']['path']
    user = update.message.from_user
    data = {
        'alert': True,
        'autorespond': True,
    'source': 'API',
    'name': user.full_name,
    'email': context.user_data['email'],
    'phone': user.id,
    'subject': 'Ticket from TG gate',
    'ip': '123.211.233.122',
    'message': context.user_data['message'],
    'attachments': [
        {DataName: DataOPrefix+file64
         }
         ]
    }
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': xapitoken
    }

    # Выполнение POST запроса
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.info("Error while creating new ticket %s ", e)
    await update.message.reply_text('Данные отправлены, проверьте почту для отслеживания обновлений!')    
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
            FILE: [MessageHandler(filters.ATTACHMENT | filters.PHOTO, get_file),CommandHandler("skip", skip_file)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)

    # Начало поиска обновлений
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()