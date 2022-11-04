from exceptions import (APIAnswerError, TLGProblemSendMSGError,
                        NotDictError, NotStatusError,
                        NoWorksError, NoRequestError)
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
    """Отправляет сообщение в Telegram чат.

    определяемый переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса Bot
    и строку с текстом сообщения.
    """
    if not bot.send_message(TELEGRAM_CHAT_ID, message):
        raise TLGProblemSendMSGError('Сообщение в Телеграм не отправлено')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.

    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response is None:
        raise NoRequestError('Ошибка при выполнении запроса')
    if response.status_code != HTTPStatus.OK:
        raise APIAnswerError(
            f'Неверный ответ от сервера. Ожидался статус ответа 200.'
            f'Получен {response.status_code}'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность.

    В качестве параметра функция получает ответ API, приведенный
    к типам данных Python. Если ответ API соответствует ожиданиям,
    то функция должна вернуть список домашних работ (он может быть и пустым),
    доступный в ответе API по ключу 'homeworks'.
    """
    if not isinstance(response, dict):
        raise TypeError('Полученный тип данных не словарь')
    if ('homeworks' or 'current_date') not in response:
        raise TypeError('В словаре отсутствуют необходимые ключи')
    homework = response['homeworks']
    if homework == []:
        raise TypeError('Информации по работам не обнаружено')
    return (homework[0])


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе статус этой работы.

    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, функция возвращает
    подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    if not isinstance(homework, dict):
        raise KeyError('Полученный тип данных не словарь')
    if ('homework_name' or 'status') not in homework:
        raise KeyError('В словаре отсутствуют необходимые ключи')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(f'Статус {homework_status}'
                       f'не соответствует ожидаемому')
    verdict = HOMEWORK_STATUSES[homework_status]
    return (f'Изменился статус проверки работы "{homework_name}".'
            f'{verdict}')


def check_tokens():
    """Проверяет доступность переменных окружения.

    которые необходимы для работы программы.
    Если отсутствует хотя бы одна переменная окружения,
    то функция должна вернуть False, иначе — True.
    """
    if (PRACTICUM_TOKEN is not None
            and TELEGRAM_TOKEN is not None
            and TELEGRAM_CHAT_ID is not None):
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    if check_tokens() is not True:
        raise SystemExit('Программа завершена')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message_one = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            current_timestamp = response.get('current_date')
            message = parse_status(homework)
            if message_one != message:
                send_message(bot, message)
                logger.info('Сообщение успешно отправлено')
                message_one = parse_status(homework)
        except (APIAnswerError, TLGProblemSendMSGError,
                NotDictError, NotStatusError, TypeError,
                KeyError, NoWorksError, NoRequestError) as error:
            message = f'Сбой в работе программы: {error}'
            if message_one != message:
                send_message(bot, message)
                message_one = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
