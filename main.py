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




def get_resume(link):
    ua = fake_useragent.UserAgent()
    data = requests.get(url=link, headers={"user-agent": ua.random})
    if data.status_code != 200:
        return
    soup = BeautifulSoup(data.content)

if __name__ == "__main__":
    for a in get_links("python"):
        print(a)