import logging
import os
from http import HTTPStatus

import requests
import telegram
import time
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TLG_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='main.log',
    filemode='w')
logger = logging.getLogger(__name__)
if logging.DEBUG:
    level = logging.DEBUG
else:
    level = logging.INFO
logger.setLevel(level)
handler = logging.StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(name)s: [%(levelname)s] %(message)s'
)
handler.setFormatter(formatter)

def send_message(bot, message):
    """Отправляет сообщение в Telegram чат, 

    определяемый переменной окружения TELEGRAM_CHAT_ID. 
    Принимает на вход два параметра: экземпляр класса Bot 
    и строку с текстом сообщения."""
    chat_id = TELEGRAM_CHAT_ID
    text = message
    bot.send_message(chat_id, text)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса. 
    
    В качестве параметра функция получает временную метку. 
    В случае успешного запроса должна вернуть ответ API, 
    преобразовав его из формата JSON к типам данных Python."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        logger.exception('"Статус ответа совсем не 200"')
        raise Exception(
            'Статус ответа не 200'
        )
    else:
        logger.info(f'Данные усепешно получены')
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность. 

    В качестве параметра функция получает ответ API, приведенный 
    к типам данных Python. Если ответ API соответствует ожиданиям, 
    то функция должна вернуть список домашних работ (он может быть и пустым), 
    доступный в ответе API по ключу 'homeworks'."""
    homework = response['homeworks']
    if homework:
        logger.info('Есть информация по работам')
        return(homework[0])
    else:
        raise TypeError('Информации по работам не обнаружено')


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы. 

    В качестве параметра функция получает только один элемент из списка 
    домашних работ. В случае успеха, функция возвращает подготовленную для отправки 
    в Telegram строку, содержащую один из вердиктов словаря HOMEWORK_STATUSES."""
    if isinstance(homework, dict):
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        return (f'Изменился статус проверки работы "{homework_name}". {verdict}')
    else:
        raise KeyError('Не верный ответ API')


def check_tokens():
    """Проверяет доступность переменных окружения, 

    которые необходимы для работы программы. 
    Если отсутствует хотя бы одна переменная окружения, 
    то функция должна вернуть False, иначе — True."""
    if PRACTICUM_TOKEN != None and TELEGRAM_TOKEN != None and TELEGRAM_CHAT_ID != None:
        return True
    else:
        logger.critical(f'Проверьте константы')
        return False

def main():
    """Основная логика работы бота."""
    if check_tokens() == True:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        message_one = None
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homework = check_response(response)
                current_timestamp = response.get('current_date')
                time.sleep(RETRY_TIME)
                message = parse_status(homework)
                if message_one != message:
                    send_message(bot, message)
                    logger.info('Сообщение успешно отправлено')
                    message_one = parse_status(homework)

            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                if message_one != message:
                    send_message(bot, message)
                    message_one = f'Сбой в работе программы: {error}'
                logger.error(message)
                time.sleep(RETRY_TIME)

if __name__ == '__main__':
    main()
