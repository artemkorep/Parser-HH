import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.executor import start_polling
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import sqlite3
from tenacity import retry, stop_after_attempt, wait_fixed

API_TOKEN = '7235202091:AAEkO5yb0EqieqRueQBNyhzFWIIbEzuyF_c'

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Создаем или подключаемся к базе данных
conn = sqlite3.connect('hh_data.db')
cursor = conn.cursor()

# Создаем таблицы для резюме и вакансий, если они не существуют
cursor.execute('''
CREATE TABLE IF NOT EXISTS resumes (
id INTEGER PRIMARY KEY,
name TEXT,
salary TEXT,
tags TEXT,
employment TEXT,
schedule TEXT,
link TEXT UNIQUE
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS vacancies (
id INTEGER PRIMARY KEY,
name TEXT,
exp TEXT,
employment TEXT,
salary TEXT,
view TEXT,
link TEXT UNIQUE
)
''')
conn.commit()

class Form(StatesGroup):
    mode = State()
    text_query = State()
    employment_type = State()
    schedule_type = State()
    salary_from = State()
    salary_to = State()
    print_text = State()
    current_page = State()
    results = State()

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def fetch(session, url):
    try:
        async with session.get(url) as response:
            if response.status != 200:
                logging.error(f"Failed to fetch {url}")
                return None
            return await response.text()
    except aiohttp.ClientError as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

async def get_links(session, text, employment='full', schedule=None, salary_from=None, salary_to=None, **filters):
    base_params = {
        'text': text,
        'area': 1,
        'isDefaultArea': 'true',
        'exp_period': 'all_time',
        'logic': 'normal',
        'pos': 'full_text',
        'page': 1,
        'order_by': 'relevance',
        'employment': employment,
        'items_on_page': 50
    }
    params = {**base_params, **filters}
    if schedule:
        params['schedule'] = schedule
    if salary_from is not None:
        params['salary_from'] = salary_from
    if salary_to is not None:
        params['salary_to'] = salary_to
    if salary_from is not None or salary_to is not None:
        params['label'] = 'only_with_salary'
    link = f"https://hh.ru/search/resume?{urlencode(params)}"
    html = await fetch(session, link)
    if html is None:
        return []
    soup = BeautifulSoup(html, 'lxml')
    try:
        page_count = int(soup.find('div', class_='pager').find_all('span', recursive=False)[-1].find('a').find('span').text)
    except:
        page_count = 1
    links = []
    tasks = []
    for page in range(page_count):
        params['page'] = page
        link = f"https://hh.ru/search/resume?{urlencode(params)}"
        tasks.append(fetch(session, link))
    results = await asyncio.gather(*tasks)
    for html in results:
        if html is None:
            continue
        soup = BeautifulSoup(html, 'lxml')
        for a in soup.find_all('a', class_='bloko-link'):
            href = a.get('href').split('?')[0]
            full_url = f"https://hh.ru{href}"
            if str(full_url).split('/')[-2] == 'resume' and str(full_url).split('/')[-1] != 'advanced':
                links.append(full_url)
    return links

async def get_resume(session, link):
    html = await fetch(session, link)
    if html is None:
        return None
    soup = BeautifulSoup(html, 'lxml')
    try:
        name = soup.find('span', class_="resume-block__title-text").text.strip()
        if not name:
            logging.error(f"Empty name found for resume at {link}. Skipping.")
            return None
    except Exception as e:
        logging.error(f"Error while fetching name for {link}: {e}")
        return None
    try:
        salary = soup.find('span', class_='resume-block__salary').text.replace('\u2009', ' ').replace('\xa0', ' ')
    except:
        salary = None
    try:
        tags = [tag.text for tag in soup.find('div', class_='bloko-tag-list').find_all('span', class_='bloko-tag__section bloko-tag__section_text')]
    except:
        tags = None
    try:
        if salary is None:
            employment = soup.find('div', class_='resume-block-container').find_all('p')[0].text
        else:
            employment = soup.find('div', class_='resume-block-item-gap').find_all('p')[0].text.replace('Занятость:', '')
    except:
        employment = None
    try:
        if salary is None:
            schedule = soup.find('div', class_='resume-block-container').find_all('p')[1].text
        else:
            schedule = soup.find('div', class_='resume-block-item-gap').find_all('p')[1].text.replace('График работы:', '')
    except:
        schedule = None
    resume = {
        "name": name,
        "salary": salary,
        "tags": ', '.join(tags) if tags else None,
        "employment": employment,
        "schedule": schedule,
        "link": link
    }
    cursor.execute('''
        INSERT OR IGNORE INTO resumes (name, salary, tags, employment, schedule, link)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, salary, ', '.join(tags) if tags else None, employment, schedule, link))
    conn.commit()
    return resume

async def get_vacancy_links(session, text, salary_from=None, salary_to=None, experience=None, schedule=None):
    base_params = {
        'text': text,
        'area': 1,
        'page': 1,
        'search_field': ['name', 'company_name', 'description'],
        'enable_snippets': 'false',
        'only_with_salary': 'true' if salary_from or salary_to else 'false'
    }
    if salary_from:
        base_params['salary_from'] = salary_from
    if salary_to:
        base_params['salary_to'] = salary_to
    if experience:
        base_params['experience'] = experience
    if schedule:
        base_params['schedule'] = schedule
    link = f"https://hh.ru/search/vacancy?{urlencode(base_params, doseq=True)}"
    html = await fetch(session, link)
    if html is None:
        return []
    soup = BeautifulSoup(html, 'lxml')
    try:
        page_count = int(soup.find('div', class_='pager').find_all('span', recursive=False)[-1].find('a').find('span').text)
    except:
        page_count = 1
    links = []
    tasks = []
    for page in range(page_count):
        base_params['page'] = page
        link = f"https://hh.ru/search/vacancy?{urlencode(base_params, doseq=True)}"
        tasks.append(fetch(session, link))
    results = await asyncio.gather(*tasks)
    for html in results:
        if html is None:
            continue
        soup = BeautifulSoup(html, 'lxml')
        for a in soup.find_all('a', class_='bloko-link'):
            href = a.get('href').split('?')[0]
            full_url = f"{href}"
            if str(full_url).split('/')[-2] == 'vacancy':
                links.append(full_url)
    return links

async def get_vacancy(session, link):
    html = await fetch(session, link)
    if html is None:
        return None
    soup = BeautifulSoup(html, 'lxml')
    try:
        name = soup.find('div', class_='vacancy-title').find('h1', class_='bloko-header-section-1').text.strip()
        if not name:
            logging.error(f"Empty name found for resume at {link}. Skipping.")
            return None
    except Exception as e:
        logging.error(f"Error while fetching name for {link}: {e}")
        return None
    try:
        exp = soup.find_all('p', class_='vacancy-description-list-item')[0].text
    except:
        exp = None
    try:
        employment = soup.find_all('p', class_='vacancy-description-list-item')[1].text
    except:
        employment = None
    try:
        salary = soup.find('div', class_='vacancy-title').find('span').text.replace('\u2009', ' ').replace('\xa0', ' ')
    except:
        salary = None
    try:
        view = soup.find('div', class_='noprint').text.replace('\u2009', ' ').replace('\xa0', ' ').replace('Откликнуться', '')
    except:
        view = None
    vacancy = {
        "name": name,
        "exp": exp,
        "employment": employment,
        "salary": salary,
        "view": view,
        "link": link
    }
    cursor.execute('''
        INSERT OR IGNORE INTO vacancies (name, exp, employment, salary, view, link)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, exp, employment, salary, view, link))
    conn.commit()
    return vacancy

@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Резюме", callback_data="resume"))
    markup.add(InlineKeyboardButton("Вакансия", callback_data="vacancy"))
    await Form.mode.set()
    await message.answer("Выберите режим поиска", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data in ['resume', 'vacancy'], state=Form.mode)
async def process_mode(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(mode=callback_query.data)
    if callback_query.data == 'resume':
        await Form.text_query.set()
        await callback_query.message.answer("Введите запрос для поиска резюме")
    else:
        await Form.text_query.set()
        await callback_query.message.answer("Введите запрос для поиска вакансии")

@dp.message_handler(state=Form.text_query)
async def process_text_query(message: types.Message, state: FSMContext):
    await state.update_data(text_query=message.text)
    user_data = await state.get_data()
    if user_data['mode'] == 'resume':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Полная занятость", callback_data="full"),
                   InlineKeyboardButton("Частичная занятость", callback_data="part"),
                   InlineKeyboardButton("Стажировка", callback_data="probation"))
        markup.add(InlineKeyboardButton("Далее", callback_data="next"))
        await Form.employment_type.set()
        await message.answer("Выберите тип занятости или пропустите", reply_markup=markup)
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Нет опыта", callback_data="noExperience"),
                   InlineKeyboardButton("От 1 года до 3 лет", callback_data="between1And3"),
                   InlineKeyboardButton("От 3 лет до 6 лет", callback_data="between3And6"),
                   InlineKeyboardButton("Более 6 лет", callback_data="moreThan6"))
        markup.add(InlineKeyboardButton("Далее", callback_data="next"))
        await Form.employment_type.set()
        await message.answer("Выберите опыт работы или пропустите", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data in ['full', 'part', 'probation', 'noExperience', 'between1And3', 'between3And6', 'moreThan6', 'next'], state=Form.employment_type)
async def process_employment_type(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data != 'next':
        await state.update_data(employment_type=callback_query.data)
    user_data = await state.get_data()
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Полный день", callback_data="fullDay"),
               InlineKeyboardButton("Удаленная работа", callback_data="remote"),
               InlineKeyboardButton("Гибкий график", callback_data="flexible"))
    markup.add(InlineKeyboardButton("Далее", callback_data="next"))
    await Form.schedule_type.set()
    await callback_query.message.answer("Выберите график работы или пропустите", reply_markup=markup)

@dp.callback_query_handler(lambda c: c.data in ['fullDay', 'remote', 'flexible', 'next'], state=Form.schedule_type)
async def process_schedule_type(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data != 'next':
        await state.update_data(schedule_type=callback_query.data)
    await Form.salary_from.set()
    await callback_query.message.answer("Введите минимальный уровень дохода или пропустите", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Пропустить", callback_data="skip_salary_from")))

@dp.callback_query_handler(lambda c: c.data == 'skip_salary_from', state=Form.salary_from)
async def skip_salary_from(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(salary_from=None)
    await Form.salary_to.set()
    await callback_query.message.answer("Введите максимальный уровень дохода или пропустите", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Пропустить", callback_data="skip_salary_to")))

@dp.message_handler(state=Form.salary_from)
async def process_salary_from(message: types.Message, state: FSMContext):
    salary_from = message.text if message.text.isdigit() else None
    await state.update_data(salary_from=salary_from)
    await Form.salary_to.set()
    await message.answer("Введите максимальный уровень дохода или пропустите", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Пропустить", callback_data="skip_salary_to")))

@dp.callback_query_handler(lambda c: c.data == 'skip_salary_to', state=Form.salary_to)
async def skip_salary_to(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(salary_to=None)
    await Form.current_page.set()
    await state.update_data(current_page=1)
    await Form.print_text.set()
    await callback_query.message.answer("Данные собраны, нажмите 'Далее', чтобы продолжить", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Далее", callback_data="print")))

@dp.message_handler(state=Form.salary_to)
async def process_salary_to(message: types.Message, state: FSMContext):
    salary_to = message.text if message.text.isdigit() else None
    await state.update_data(salary_to=salary_to)
    await Form.current_page.set()
    await state.update_data(current_page=1)
    await Form.print_text.set()
    await message.answer("Данные собраны, нажмите 'Далее', чтобы продолжить", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Далее", callback_data="print")))

@dp.callback_query_handler(lambda c: c.data == 'print', state=Form.print_text)
async def process_print(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    mode = user_data['mode']
    text_query = user_data['text_query']
    employment_type = user_data.get('employment_type')
    schedule_type = user_data.get('schedule_type')
    salary_from = user_data.get('salary_from')
    salary_to = user_data.get('salary_to')
    current_page = user_data.get('current_page', 1)
    results = user_data.get('results', [])

    filters = (
        f"Режим: {'Резюме' if mode == 'resume' else 'Вакансия'}\n"
        f"Запрос: {text_query}\n"
        f"Тип занятости: {employment_type or 'Не указано'}\n"
        f"График работы: {schedule_type or 'Не указано'}\n"
        f"Минимальная зарплата: {salary_from or 'Не указано'}\n"
        f"Максимальная зарплата: {salary_to or 'Не указано'}"
    )

    await callback_query.message.answer(f"Ожидайте! Вот ваши фильтры:\n{filters}")

    start_index = (current_page - 1) * 5
    end_index = start_index + 5

    if not results:
        async with aiohttp.ClientSession() as session:
            if mode == 'resume':
                links = await get_links(session, text_query, employment=employment_type, schedule=schedule_type, salary_from=salary_from, salary_to=salary_to)
                tasks = [get_resume(session, link) for link in links[:50]]  # Ограничиваем число запросов
            else:
                links = await get_vacancy_links(session, text_query, salary_from=salary_from, salary_to=salary_to, experience=employment_type, schedule=schedule_type)
                tasks = [get_vacancy(session, link) for link in links[:50]]  # Ограничиваем число запросов

            new_results = await asyncio.gather(*tasks)
            results.extend([res for res in new_results if res])
            await state.update_data(results=results)

    for result in results[start_index:end_index]:
        if mode == 'resume':
            await callback_query.message.answer(
                f"Резюме: {result['name']}\nЗарплата: {result['salary']}\nТеги: {result['tags']}\nЗанятость: {result['employment']}\nГрафик: {result['schedule']}\nСсылка: {result['link']}"
            )
        else:
            await callback_query.message.answer(
                f"Вакансия: {result['name']}\nОпыт: {result['exp']}\nЗанятость: {result['employment']}\nЗарплата: {result['salary']}\nПросмотры: {result['view']}\nСсылка: {result['link']}"
            )

    markup = InlineKeyboardMarkup()
    if len(results) > end_index:
        markup.add(InlineKeyboardButton("Продолжить поиск", callback_data="print"))
    markup.add(InlineKeyboardButton("Аналитика", callback_data="analytics"))
    markup.add(InlineKeyboardButton("Завершить", callback_data="finish"))
    await callback_query.message.answer("Продолжить дальше, либо завершить поиск", reply_markup=markup)

    await state.update_data(current_page=current_page + 1)

@dp.callback_query_handler(lambda c: c.data == 'analytics', state=Form.print_text)
async def process_analytics(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    mode = user_data['mode']
    results = user_data.get('results', [])

    count = len(results)
    total_salary = 0
    salary_count = 0

    for result in results:
        salary = result['salary']
        if salary and salary.lower() != 'не указано':
            try:
                salary_value = int(''.join(filter(str.isdigit, salary.split()[0])))
                total_salary += salary_value
                salary_count += 1
            except ValueError:
                continue

    avg_salary = total_salary // salary_count if salary_count > 0 else "не указано"

    await callback_query.message.answer(
        f"Количество доступных {'резюме' if mode == 'resume' else 'вакансий'}: {count}\nСредняя зарплата: {avg_salary}"
    )

@dp.callback_query_handler(lambda c: c.data == 'finish', state="*")
async def process_finish(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await cmd_start(callback_query.message)

async def on_startup(dp):
    logging.info('Bot started')

async def on_shutdown(dp):
    logging.warning('Shutting down..')
    await dp.storage.close()
    await dp.storage.wait_closed()
    logging.warning('Bye!')

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)
