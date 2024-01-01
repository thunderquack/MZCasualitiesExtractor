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
bo_pattern = r'bo\s*=\s*JSON\.parse\(\'({.*?})\'\)'
# Поиск соответствия в файле
bo_match = re.search(bo_pattern, js, re.DOTALL)
# Если найдено соответствие, извлекаем и суммируем все числа
start_date = datetime(2022, 2, 24)

# Path to the 'docs' directory
docs_path = './docs'

csv_filename = f'{docs_path}/last_data.csv'
chart_file_name = "7days.svg"
current_date = datetime.now().strftime('%Y-%m-%d')
current_date_csv = f'{docs_path}/{current_date}_cumsum.csv'
chart_path = f'{docs_path}/{chart_file_name}'

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

    except json.JSONDecodeError as e:
        total_sum_bo = f"Error parsing JSON for 'bo': {e}"
        print(total_sum_bo)
        exit(998)
else:
    total_sum_bo = "No match for variable 'bo' found."
    print(total_sum_bo)
    exit(998)

if not os.path.exists(docs_path):
    os.mkdir(docs_path)

df.to_csv(csv_filename, index=False)
df.to_csv(current_date_csv, index=False)

df.set_index('date', inplace=True)
weekly_sum = df['change'].resample('7D').sum()

total_casualities = df['change'].sum()

# Построим новую столбчатую диаграмму

plt.figure(figsize=(15, 7))
weekly_sum.plot(kind='bar', color='royalblue')
plt.title('Casualities / Week')
plt.xlabel('Date')
plt.ylabel('Casualities')
plt.xticks(ticks=range(len(weekly_sum.index)), labels=[d.strftime('%Y-%m-%d') for d in weekly_sum.index], rotation=90)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

plt.savefig(chart_path)
plt.close()

# Get a list of csv files in the docs directory, excluding last_data.csv
csv_files = [f for f in os.listdir(docs_path) if f.endswith('.csv') and f != 'last_data.csv']

# Sort files by date, assuming the format 'YYYY-MM-DD_filename.csv'
csv_files.sort(reverse=True)

# Add HTML list items for each CSV file
for filename in csv_files:
    if filename != 'last_data.csv':
        markdown_content += f"- [{filename}]({filename})\n"

markdown_content+=f"<br>![7-Day Intervals Bar Chart]({chart_file_name})\n"

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
# Russian Army verified losses

## Losses

As of **{current_date}** there are **{total_casualities}** confirmed[^1] fatalities

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
