import httpx
import re
import time
import json
import pandas as pd
from datetime import timedelta
from datetime import datetime
import os
import markdown
import matplotlib.pyplot as plt
import subprocess

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

# Define the markdown content
markdown_content = """
# Russian Army verified losses

## Index of CSV Files

Welcome to the CSV index.

### Latest Data

Download the [latest data](last_data.csv)

### Historical Data

Below are the historical data files:

"""

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
# там барахло вида {"0":[4,36,3, и т.п., строк 19 штук, а внутри на каждый день потеря
# попробуй найди этот кусок - найдешь нужную переменную

so_pattern = r'SA\s*=\s*JSON\.parse\s*\(\s*\'({.*?})\'\s*\)'
bo_match_string = re.search(so_pattern, js, re.DOTALL)
# Если найдено соответствие, извлекаем и суммируем все числа
start_date = datetime(2022, 2, 24)

# Path to the 'docs' directory
docs_path = './docs'

csv_filename = f'{docs_path}/last_data.csv'
chart_file_name = "7days.svg"
current_date = datetime.now().strftime('%Y-%m-%d')
current_date_csv = f'{docs_path}/{current_date}_cumsum.csv'
chart_path = f'{docs_path}/{chart_file_name}'

if bo_match_string:
    try:
        # Извлекаем JSON из строки и преобразуем его в объект Python
        bo_data = json.loads(bo_match_string.group(1))
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

    except json.JSONDecodeError as e:
        total_sum_bo = f"Error parsing JSON for 'bo': {e}"
        print(total_sum_bo)
        exit(998)
else:
    total_sum_bo = "No match for variable 'bo' found."
    print(total_sum_bo)
    exit(998)

sum_pattern = r'{\"w\":\"current_total\",\"rnd\":.*?,\"real\":(.*?)}'
sum_result = re.search(sum_pattern, js, re.DOTALL)

sum_v = 0
sum_o = 0

if (sum_result):
    sum_v = sum_result.group(1)

if not os.path.exists(docs_path):
    os.mkdir(docs_path)

df.to_csv(csv_filename, index=False)
df.to_csv(current_date_csv, index=False)

command = ['git', 'show', f'HEAD:{csv_filename}']
# Выполнение команды и получение результата
try:
    result = subprocess.check_output(command, universal_newlines=True)
    with open('extracted_last_data.csv', 'w') as file:
        file.write(result)
    print("Файл успешно извлечен.")
except subprocess.CalledProcessError as e:
    print(f"Ошибка при выполнении команды: {e}")

df.set_index('date', inplace=True)
weekly_sum = df['change'].resample('7D').sum()

total_casualties = df['change'].sum()

csv_files = sorted([f for f in os.listdir(docs_path)
                   if f.endswith('.csv')], reverse=True)

# Считывание содержимого самого нового файла
current_file_path = os.path.join(docs_path, csv_files[0])
with open(current_file_path, 'r') as file:
    current_content = file.read()

# Итерация по файлам в обратном порядке времени
for previous_file in csv_files[1:]:
    previous_file_path = os.path.join(docs_path, previous_file)
    with open(previous_file_path, 'r') as file:
        previous_content = file.read()

    # Сравнение содержимого файла с текущим
    if previous_content != current_content:
        # Файл найден, выводим его дату и прерываем цикл
        print(f"Содержимое файла изменилось в: {previous_file}")
        break
    else:
        # Обновление "текущего" содержимого для следующей итерации сравнения
        current_content = previous_content

previous_data = pd.read_csv(f'{docs_path}/{previous_file}')
previous_data['date'] = pd.to_datetime(previous_data['date'])
previous_data.set_index('date', inplace=True)
previous_weekly_sum = previous_data['change'].resample('7D').sum()
difference = weekly_sum.subtract(previous_weekly_sum, fill_value=0).astype(int)

# Построим новую столбчатую диаграмму

plt.figure(figsize=(15, 7))
weekly_sum.index = pd.to_datetime(weekly_sum.index)
difference.index = pd.to_datetime(difference.index)
plt.bar(weekly_sum.index, weekly_sum-difference,
        width=5, color='royalblue', label='Weekly Sum')
plt.bar(difference.index, difference, bottom=weekly_sum-difference,
        width=5, color='forestgreen', label='Difference')
for idx, (ws_val, diff_val) in enumerate(zip(weekly_sum-difference, difference)):
    if diff_val != 0:  # Если разница не равна нулю, показываем подпись
        plt.text(weekly_sum.index[idx], ws_val + diff_val,
                 f'{diff_val}', ha='center', va='bottom', color='forestgreen')
plt.title('Casualities / Week')
plt.xlabel('Date')
plt.ylabel('Casualities')
plt.xticks(ticks=weekly_sum.index, labels=[d.strftime(
    '%Y-%m-%d') for d in weekly_sum.index], rotation=90)
plt.grid(axis='y', linestyle='--', alpha=0.7)
# plt.legend()
plt.tight_layout()
plt.savefig(chart_path)
plt.close()

# Get a list of csv files in the docs directory, excluding last_data.csv
csv_files = [f for f in os.listdir(docs_path) if f.endswith(
    '.csv') and f != 'last_data.csv']

# Sort files by date, assuming the format 'YYYY-MM-DD_filename.csv'
csv_files.sort(reverse=True)

# Add HTML list items for each CSV file
for filename in csv_files:
    if filename != 'last_data.csv':
        markdown_content += f"- [{filename}]({filename})\n"

markdown_content += f"<br>![7-Day Intervals Bar Chart]({chart_file_name})\n"

# Convert markdown to HTML
html_content = markdown.markdown(markdown_content)

# Start of our HTML content
html_document = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Russian Army verified losses</title>
</head>
<body>
    {html_content}
</body>
</html>
"""

# Write the HTML content to index.html in the 'docs' directory
with open(os.path.join(docs_path, 'index.html'), 'w') as html_file:
    html_file.write(html_document)

readme_document = f"""
# Confirmed Losses of the Russian Army

## Casualties

As of **{current_date}**, there have been **{sum_v}** confirmed[^1] fatalities.
Of these, **{total_casualties}** have a known date of death.

## Chart

![7-Day Intervals Bar Chart]({chart_path})

## Archive

https://thunderquack.github.io/MZCasualitiesExtractor

## Source

https://zona.media/casualties

---

[^1]: "Confirmed" means each death is supported by a name, obituary, tomb photo, etc.
"""

with open('README.md', 'w') as readme_file:
    readme_file.write(readme_document)
