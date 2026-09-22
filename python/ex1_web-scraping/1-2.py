#open ~/.cache/selenium/chromedriver/ これをターミナルで実行すると使ったChromeドライバーのフォルダが開く　
from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time 
from normalize_japanese_addresses import normalize

df = pd.DataFrame(columns = ['店舗名', '電話番号', 'メールアドレス', '都道府県', '市区町村', '番地', '建物名', 'URL', 'SSL'])
driver = webdriver.Chrome()
target_url = 'https://r.gnavi.co.jp/area/fukuoka/rs/?cuisine=MIZUTAKI%2CMOTUNABE&sort=HIGH'
driver.get(target_url)
time.sleep(3)

num_limit = 30
seen_url = set()
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"}

for page in range(2):
    res = requests.get(target_url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    num = 0
    shop_page = soup.find_all("a", href=re.compile(r"^https://r.gnavi.co.jp/[a-z0-9]+/$"))

    for a in dict.fromkeys(shop_page):
        url = a.get("href")
        time.sleep(3)

        if url in seen_url:
            continue
        seen_url.add(url)

        res = requests.get(url, headers=headers)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, "html.parser")
        item = soup.find("table", class_="basic-table")

        name = item.find("p")
        name = name.text if name else ""
        number = item.find("span", class_ = "number")
        number = number.text if number else ""
    
        mail = ""
        for tr in item.find_all("tr"):
            th = tr.find("th")
            td = tr.find("td")
            if th and td and "メール" in th.text:
                mail = td.text
        mailto = item.find("a", href=re.compile(r"mailto:"))
        if mailto:
            mail = mailto.get("href").replace("mailto:", "").split("?")[0]

        address = item.find("span", class_="region")
        nomalized_address = normalize(address.text)
        pref = nomalized_address["pref"]
        city = nomalized_address["city"]
        town = nomalized_address["town"]
        citytown = city + town
        addr = nomalized_address["addr"]

        bil = item.find("span", class_ = "locality")
        bil = bil.text if bil else ""

        official = soup.find("a", title = "オフィシャルページ")
        shop_url = ""
        ssl_info = ""

        if official:
            raw_href = official.get("href", "")
            shop_url = raw_href.split("?")[0]
            if shop_url.startswith("https://"):
                try:
                    head = requests.head(shop_url, headers=headers, verify=True, timeout = 5, allow_redirects=True)
                    if head.status_code >= 400:
                        head = requests.get(url, headers=headers, verify=True, timeout=5, stream=True)
                    ssl_info = "True"
                except requests.exceptions.SSLError:
                    ssl_info = "False"

        list = [name, number, mail, pref, citytown, addr, bil, shop_url, ssl_info]
        df.loc[len(df)] = list

        num += 1
        if num == num_limit:
            break        

    next = driver.find_element(By.CSS_SELECTOR, '[alt*="次"]')
    next.click()
    time.sleep(3)

    target_url = driver.current_url
    num_limit = 20

driver.quit()

df.to_csv('1-2.csv', mode='w', encoding='utf-8-sig', index=False)
