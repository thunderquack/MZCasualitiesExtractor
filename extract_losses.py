import httpx
import re
import time
import json
import pandas as pd
from datetime import timedelta
from datetime import datetime

mz_page = 'https://zona.media/casualties'
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-GB",
    "Accept-Encoding": "gzip",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "?1"
}

url_pattern = r'https://[a-zA-Z0-9.-]*/infographics/bodycount/[a-zA-Z0-9.-]*\.js\.gz'

max_attempts = 100
attempt = 0

while attempt < max_attempts:
    try:
        client = httpx.Client(http2=True)
        response = client.get(mz_page, headers=headers)
        if response.status_code == 200:
            print('js is found')
            page_content = response.text
            js_gz_urls = re.findall(url_pattern, page_content)
            url_js = js_gz_urls[0] if js_gz_urls else "URL is not found"
            print(f"Found JS URL: {url_js}")
            response = client.get(url_js, headers=headers)
            js = response.text
            print(js)
            break  # Если успешно, выходим из цикла
        else:
            print(f"Error loading page: {response.status_code}")
            attempt += 1
            time.sleep(1)  # Задержка перед следующей попыткой
    except httpx.RequestError as e:
        print(f"Connection error on attempt {attempt}: {e}")
        attempt += 1
        time.sleep(1)  # Задержка перед следующей попыткой

if attempt == max_attempts:
    print(f"Failed to retrieve the page after {max_attempts} attempts.")
    exit(999)

# Паттерн для извлечения значения переменной 'bo'
bo_pattern = r'bo\s*=\s*JSON\.parse\(\'({.*?})\'\)'
# Поиск соответствия в файле
bo_match = re.search(bo_pattern, js, re.DOTALL)
# Если найдено соответствие, извлекаем и суммируем все числа
start_date = datetime(2022, 2, 24)
csv_filename = 'last_data.csv'
current_date = datetime.now().strftime('%Y-%m-%d')
current_date_csv = f'{current_date}_cumsum.csv'

if bo_match:
    try:
        # Извлекаем JSON из строки и преобразуем его в объект Python
        bo_data = json.loads(bo_match.group(1))
        rows = len(bo_data)
        max_len = 0
        for key in bo_data:
            max_len = max(len(bo_data[key]), max_len)
        dates = list()
        deltas = list()
        for i in range(max_len):
            date = start_date+timedelta(days=i)
            dates.append(date)
            s = 0
            for key in bo_data:
                try:
                    s += bo_data[key][i]
                except:
                    pass
            deltas.append(s)
        data = {
            "date": dates,
            "change": deltas,
        }
        df = pd.DataFrame(data)
        df['total'] = df['change'].cumsum()
        df.to_csv(csv_filename, index=False)
        df.to_csv(current_date_csv, index=False)

    except json.JSONDecodeError as e:
        total_sum_bo = f"Error parsing JSON for 'bo': {e}"
        print(total_sum_bo)
        exit(998)
else:
    total_sum_bo = "No match for variable 'bo' found."
    print(total_sum_bo)
    exit(998)
