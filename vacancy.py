import requests
from bs4 import BeautifulSoup
import fake_useragent
import time
import sqlite3
from urllib.parse import urlencode

def get_links(text):
    ua = fake_useragent.UserAgent()

    # Построение URL с параметрами
    link = f"https://hh.ru/search/vacancy?text={text}&area=1&page=1"
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
            link = f"https://hh.ru/search/vacancy?text={text}&area=1&page={page}"
            data = requests.get(url=link, headers={"user-agent": ua.random})
            if data.status_code != 200:
                continue
            soup = BeautifulSoup(data.content, 'lxml')
            for a in soup.find_all('a', class_='bloko-link'):
                href = a.get('href').split('?')[0]
                full_url = f"{href}"
                if str(full_url).split('/')[-2] == 'vacancy':
                    yield full_url
        except Exception as e:
            print(f"Error during link fetching: {e}")
            time.sleep(1)


# ua = fake_useragent.UserAgent()
# data = requests.get(url='https://hh.ru/vacancy/102551587', headers={"user-agent": ua.random})
# soup = BeautifulSoup(data.content, 'lxml')
# name = soup.find('div', class_='vacancy-title').find('h1', class_='bloko-header-section-1').text
# exp = soup.find_all('p', class_='vacancy-description-list-item')[0].text
# employment = soup.find_all('p', class_='vacancy-description-list-item')[1].text
# salary = soup.find('div', class_='vacancy-title').find('span').text.replace('\u2009', ' ').replace('\xa0', ' ')
# view = soup.find('div', class_='noprint').text.replace('\u2009', ' ').replace('\xa0', ' ').replace('Откликнуться', '')
# print(name, exp, employment, salary)

def get_vacancy(link):
    ua = fake_useragent.UserAgent()
    data = requests.get(url=link, headers={"user-agent": ua.random})
    if data.status_code != 200:
        print(f"Failed to fetch resume from {link}")
        return
    soup = BeautifulSoup(data.content, 'lxml')

    # Название вакансии
    try:
        name = soup.find('div', class_='vacancy-title').find('h1', class_='bloko-header-section-1').text
        if not name.strip():  # Проверяем, что name не пустое
            print(f"Empty name found for resume at {link}. Skipping.")
            return
    except Exception as e:
        print(f"Error while fetching name for {link}: {e}")
        return

    # Опыт
    try:
        exp = soup.find_all('p', class_='vacancy-description-list-item')[0].text
    except:
        exp = None

    # Занятость
    try:
        employment = soup.find_all('p', class_='vacancy-description-list-item')[1].text
    except:
        employment = None

    # Зарплата
    try:
        salary = soup.find('div', class_='vacancy-title').find('span').text.replace('\u2009', ' ').replace('\xa0', ' ')
    except:
        salary = None

    # Смотрит вакансию
    try:
        view = soup.find('div', class_='noprint').text.replace('\u2009', ' ').replace('\xa0', ' ').replace('Откликнуться', '')
    except:
        view = None

    vacancy = {
        "name": name,
        "exp": exp,
        "employment": employment,
        "salary": salary,
        "view": view
    }


    # Вставка данных в базу данных
    try:
        conn = sqlite3.connect('main.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO vacancies (name, exp, employment, salary, view)
            VALUES (?, ?, ?, ?, ?)
        ''', (vacancy['name'], vacancy['exp'], vacancy['employment'], vacancy['salary'], vacancy['view']))
        conn.commit()
        conn.close()
        print(f"Added vacancy to database: {vacancy}")
    except Exception as e:
        print(f"Error during database insertion: {e}")


if __name__ == "__main__":
    for link in get_links('python'):
        get_vacancy(link)
        time.sleep(1)
