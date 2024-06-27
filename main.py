import requests
from bs4 import BeautifulSoup
import fake_useragent
import time
import sqlite3
from urllib.parse import urlencode

def get_links(text, employment='full', schedule=None, salary_from=None, salary_to=None, **filters):
    ua = fake_useragent.UserAgent()

    # Базовые параметры запроса
    base_params = {
        'text': text,
        'area': 1,
        'isDefaultArea': 'true',
        'exp_period': 'all_time',
        'logic': 'normal',
        'pos': 'full_text',
        'page': 1,
        'order_by': 'relevance',
        'employment': employment,  # добавлен параметр employment
        'items_on_page': 50
    }

    # Объединение базовых параметров с дополнительными фильтрами
    params = {**base_params, **filters}

    # Добавление параметров графика работы, если они указаны
    if schedule:
        params['schedule'] = schedule

    # Добавление параметров зарплаты, если они указаны
    if salary_from is not None:
        params['salary_from'] = salary_from
    if salary_to is not None:
        params['salary_to'] = salary_to
    if salary_from is not None or salary_to is not None:
        params['label'] = 'only_with_salary'

    # Построение URL с параметрами
    link = f"https://hh.ru/search/resume?{urlencode(params)}"
    data = requests.get(url=link, headers={"user-agent": ua.random})

    if data.status_code != 200:
        return

    soup = BeautifulSoup(data.content, 'lxml')

    try:
        page_count = int(
            soup.find('div', class_='pager').find_all('span', recursive=False)[-1].find('a').find('span').text)
    except:
        page_count = 1  # Если количество страниц не найдено, предполагаем одну страницу

    for page in range(page_count):
        try:
            params['page'] = page
            link = f"https://hh.ru/search/resume?{urlencode(params)}"
            data = requests.get(url=link, headers={"user-agent": ua.random})
            if data.status_code != 200:
                continue
            soup = BeautifulSoup(data.content, 'lxml')
            for a in soup.find_all('a', class_='bloko-link'):
                href = a.get('href').split('?')[0]
                full_url = f"https://hh.ru{href}"
                yield full_url
        except Exception as e:
            print(f"Error during link fetching: {e}")
            time.sleep(1)

def get_resume(link):
    ua = fake_useragent.UserAgent()
    data = requests.get(url=link, headers={"user-agent": ua.random})
    if data.status_code != 200:
        print(f"Failed to fetch resume from {link}")
        return
    soup = BeautifulSoup(data.content, 'lxml')

    # Название резюме
    try:
        name = soup.find('span', class_="resume-block__title-text").text
        if not name.strip():  # Проверяем, что name не пустое
            print(f"Empty name found for resume at {link}. Skipping.")
            return
    except Exception as e:
        print(f"Error while fetching name for {link}: {e}")
        return

    # Зарплата
    try:
        salary = soup.find('span', class_='resume-block__salary').text.replace('\u2009', ' ').replace('\xa0', ' ')
    except:
        salary = None

    # Ключевые навыки
    try:
        tages = soup.find('div', class_='bloko-tag-list').find_all('span', class_='bloko-tag__section bloko-tag__section_text')
        tag_texts = [tag.text for tag in tages]
        tags = ', '.join(tag_texts)  # Преобразуем список тегов в строку
    except:
        tags = None

    # Занятость
    try:
        employment = str(soup.find('div', class_='resume-block-container').find_all('p')[0].text)
    except:
        employment = None

    # График работы
    try:
        schedule = str(soup.find('div', class_='resume-block-container').find_all('p')[1].text)
    except:
        schedule = None

    resume = {
        "name": name,
        "salary": salary,
        "tags": tags,
        "employment": employment,
        "schedule": schedule
    }

    # Вставка данных в базу данных
    try:
        conn = sqlite3.connect('main.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO resumes (name, salary, tags, employment, schedule)
            VALUES (?, ?, ?, ?, ?)
        ''', (resume['name'], resume['salary'], resume['tags'], resume['employment'], resume['schedule']))
        conn.commit()
        conn.close()
        print(f"Added resume to database: {resume}")
    except Exception as e:
        print(f"Error during database insertion: {e}")

if __name__ == "__main__":
    filters = {
        'hhtmFrom': 'resume_search_form',
        'relocation': 'living_or_relocation',
        'gender': 'unknown',
        'search_period': 0,
        'filter_exp_period': 'all_time'
    }
    employment_type = input("Enter employment type (full, part, probation): ")
    schedule_type = input("Enter schedule type (fullDay, remote, flexible, or leave blank): ")
    salary_from = input("Enter minimum salary (or leave blank): ")
    salary_to = input("Enter maximum salary (or leave blank): ")

    # Преобразование пустых строк в None
    salary_from = int(salary_from) if salary_from else None
    salary_to = int(salary_to) if salary_to else None

    for link in get_links('python', employment=employment_type, schedule=schedule_type, salary_from=salary_from, salary_to=salary_to, **filters):
        get_resume(link)
        time.sleep(1)
