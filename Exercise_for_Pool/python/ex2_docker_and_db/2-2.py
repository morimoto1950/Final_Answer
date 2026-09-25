import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time 
from normalize_japanese_addresses import normalize
from sqlalchemy import create_engine

engine = create_engine(f"mysql+pymysql://ex2user:ex2pass@db:3306/ex2?charset=utf8mb4")

df = pd.DataFrame(columns = ['店舗名', '電話番号', 'メールアドレス', '都道府県', '市区町村', '番地', '建物名', 'URL', 'SSL'])
url1 = 'https://r.gnavi.co.jp/area/fukuoka/rs/?cuisine=MIZUTAKI%2CMOTUNABE&sort=HIGH'
url2 = 'https://r.gnavi.co.jp/area/fukuoka/rs/?cuisine=MIZUTAKI%2CMOTUNABE&sort=HIGH&p=2'

target_url = url1
num_limit = 30

seen_url = set()
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"}

for page in range(2):
    res = requests.get(target_url, headers = headers)
    soup = BeautifulSoup(res.text, "html.parser")
    num = 0
    shop_page = soup.find_all("a", href = re.compile(r"^https://r.gnavi.co.jp/[a-z0-9]+/$"))

    for a in dict.fromkeys(shop_page):
        url = a.get("href")
        time.sleep(3)

        if url in seen_url:
            continue
        seen_url.add(url)

        res = requests.get(url, headers = headers)
        res.encoding = res.apparent_encoding#文字化けの呪文？
        soup = BeautifulSoup(res.text, "html.parser")
        item = soup.find("table", class_ = "basic-table")
 
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


    target_url = url2
    num_limit = 20

df.to_sql('ex2_2', con=engine, if_exists='replace', index=False)
print(f"{len(df)}件のデータをex2.ex2_2に格納しました。")