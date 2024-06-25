import requests
from bs4 import BeautifulSoup
import fake_useragent
import time
import json

def get_links(text):
    ua = fake_useragent.UserAgent()
    link = f"https://hh.ru/search/resume?text={text}&area=1&isDefaultArea=true&exp_period=all_time&logic=normal&pos=full_text&page=1/"
    data = requests.get(url=link, headers={"user-agent":ua.random})
    if data.status_code != 200:
        return
    soup = BeautifulSoup(data.content, 'lxml')
    try:
        page_count = int(soup.find('div', class_='pager').find_all('span', recursive=False)[-1].find('a').find('span').text)
    except:
        return
    for page in range(page_count):
        try:
            link = f"https://hh.ru/search/resume?text={text}&area=1&isDefaultArea=true&exp_period=all_time&logic=normal&pos=full_text&page={page}/"
            data = requests.get(url=link, headers={"user-agent": ua.random})
            if data.status_code != 200:
                continue
            soup = BeautifulSoup(data.content, 'lxml')
            for a in soup.find_all('a', class_='bloko-link'):
                href = a.get('href').split('?')[0]
                full_url = f"https://hh.ru{href}"
                yield full_url
                #yield f"https://hh.ru{a.get('href')}"
        except Exception as e:
            print(f"{e}")
            time.sleep(1)

# ua = fake_useragent.UserAgent()
# data = requests.get(url='https://hh.ru/resume/2756fa070003af688e0039ed1f4f4777794744?query=python&searchRid=1719332583299e3d13d5b0eef868cf04&hhtmFrom=resume_search_result', headers={"user-agent": ua.random})
# soup = BeautifulSoup(data.content, 'lxml')
# tags = soup.find('div', class_='bloko-tag-list').find_all('span', class_='bloko-tag__section bloko-tag__section_text')
# tag_texts = [tag.text for tag in tags]
# print(tag_texts)


def get_resume(link):
    ua = fake_useragent.UserAgent()
    data = requests.get(url=link, headers={"user-agent": ua.random})
    if data.status_code != 200:
        return
    soup = BeautifulSoup(data.content, 'lxml')
    # Название резюме
    try:
        name = soup.find('span', class_="resume-block__title-text").text
    except:
        name = None

    # Зарплата
    try:
        salary = soup.find('span', class_='resume-block__salary').text.replace('\u2009', '').replace('\xa0', '')
    except:
        salary = None

    # Ключевые навыки
    try:
        tages = soup.find('div', class_='bloko-tag-list').find_all('span', class_='bloko-tag__section bloko-tag__section_text')
        tag_texts = [tag.text for tag in tages]
        tags = tag_texts
    except:
        tags = None

    resume = {
        "name":name,
        "salary":salary,
        "tags":tags
    }
    return resume


if __name__ == "__main__":
    data = []
    for a in get_links("python"):
        data.append(get_resume((a)))
        time.sleep(1)
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data,f,indent=4, ensure_ascii=False)