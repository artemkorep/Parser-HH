import requests
from bs4 import BeautifulSoup
import fake_useragent
import time
import sqlite3
from urllib.parse import urlencode

# def get_links(text):
#     ua = fake_useragent.UserAgent()
#
#     # Построение URL с параметрами
#     link = f"https://hh.ru/search/vacancy?text={text}&area=1&page=1"
#     data = requests.get(url=link, headers={"user-agent": ua.random})
#
#     if data.status_code != 200:
#         return
#
#     soup = BeautifulSoup(data.content, 'lxml')
#
#     try:
#         page_count = int(
#             soup.find('div', class_='pager').find_all('span', recursive=False)[-1].find('a').find('span').text)
#     except:
#         page_count = 1  # Если количество страниц не найдено, предполагаем одну страницу
#
#     for page in range(page_count):
#         try:
#             link = f"https://hh.ru/search/vacancy?text={text}&area=1&page={page}"
#             data = requests.get(url=link, headers={"user-agent": ua.random})
#             if data.status_code != 200:
#                 continue
#             soup = BeautifulSoup(data.content, 'lxml')
#             for a in soup.find_all('a', class_='bloko-link'):
#                 href = a.get('href').split('?')[0]
#                 full_url = f"{href}"
#                 if str(full_url).split('/')[-2] == 'vacancy':
#                     yield full_url
#         except Exception as e:
#             print(f"Error during link fetching: {e}")
#             time.sleep(1)


ua = fake_useragent.UserAgent()
data = requests.get(url='https://hh.ru/vacancy/102551587', headers={"user-agent": ua.random})
soup = BeautifulSoup(data.content, 'lxml')
name = soup.find('div', class_='vacancy-title').find('h1', class_='bloko-header-section-1').text
exp = soup.find_all('p', class_='vacancy-description-list-item')[0].text
employment = soup.find_all('p', class_='vacancy-description-list-item')[1].text
salary = soup.find('div', class_='vacancy-title').find('span').text.replace('\u2009', ' ').replace('\xa0', ' ')
view = soup.find('div', class_='noprint').text.replace('\u2009', ' ').replace('\xa0', ' ')
print(name, exp, employment, salary)
print(view)
# def get_vacancy(link):
#     ua = fake_useragent.UserAgent()
#     data = requests.get(url=link, headers={"user-agent": ua.random})
#     if data.status_code != 200:
#         print(f"Failed to fetch resume from {link}")
#         return
#     soup = BeautifulSoup(data.content, 'lxml')
#
#     # Название вакансии
#     try:
#         name = soup.find('div', class_='vacancy-title').find('h1', class_='bloko-header-section-1').text
#         if not name.strip():  # Проверяем, что name не пустое
#             print(f"Empty name found for resume at {link}. Skipping.")
#             return
#     except Exception as e:
#         print(f"Error while fetching name for {link}: {e}")
#         return
#
#     # # Зарплата
#     # try:
#     #     salary = soup.find('span', class_='bloko-header-section-2 bloko-header-section-2_lite').text.replace('\u2009', ' ').replace('\xa0', ' ')
#     # except:
#     #     salary = None
#     #
#     # # Ключевые навыки
#     # try:
#     #     tags = soup.find('div', class_='bloko-tag-list').find_all('span', class_='bloko-tag__section bloko-tag__section_text')
#     #     tag_texts = [tag.text for tag in tags]
#     #     tags = ', '.join(tag_texts)  # Преобразуем список тегов в строку
#     # except:
#     #     tags = None
#     #
#     # # Занятость
#     # try:
#     #     employment = str(soup.find('p', class_='vacancy-description-list-item').text)
#     # except:
#     #     employment = None
#
#     resume = {
#         "name": name,
#     }
#
#     print(resume)
#
#     # # Вставка данных в базу данных
#     # try:
#     #     conn = sqlite3.connect('resumes.db')
#     #     cursor = conn.cursor()
#     #     cursor.execute('''
#     #         INSERT INTO resumes (name, salary, tags, employment)
#     #         VALUES (?, ?, ?, ?)
#     #     ''', (resume['name'], resume['salary'], resume['tags'], resume['employment']))
#     #     conn.commit()
#     #     conn.close()
#     #     print(f"Added resume to database: {resume}")
#     # except Exception as e:
#     #     print(f"Error during database insertion: {e}")
#
# if __name__ == "__main__":
#
#     for link in get_links('python'):
#         get_vacancy(link)
#         time.sleep(1)
