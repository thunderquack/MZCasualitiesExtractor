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

url_pattern = r'https://[a-zA-Z0-9.-]+/infographics/bodycount/[a-zA-Z0-9.-]+\.js(?:\.(?:gz|br))?'

with httpx.Client(http2=True, follow_redirects=True, timeout=30) as client:
    for attempt in range(3):
        try:
            response = client.get(mz_page, headers=headers)
            response.raise_for_status()
            urls = re.findall(url_pattern, response.text)
            if not urls:
                raise ValueError("Source page contains no bodycount JavaScript URL")
            print(f"Found JS URL: {urls[-1]}", flush=True)
            response = client.get(urls[-1], headers=headers)
            response.raise_for_status()
            js = response.text
            break
        except (httpx.RequestError, httpx.HTTPStatusError) as error:
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code < 500 and error.response.status_code != 429:
                raise
            if attempt == 2:
                raise
            print(f"Temporary download error: {error}", flush=True)
            time.sleep(2)

# Паттерн для извлечения значения переменной 'bo'
# там барахло вида {"0":[4,36,3, и т.п., строк 19 штук, а внутри на каждый день потеря
# попробуй найди этот кусок - найдешь нужную переменную

so_pattern = r',[a-zA-Z]A\s*=\s*JSON\.parse\s*\(\s*\'({.*?})\'\s*\)'
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

# Identify embedded payloads by structure rather than minified variable names.
payloads = []
for match in re.finditer(r"JSON\.parse\(\s*'((?:\\.|[^'\\])*)'\s*\)", js):
    # The source uses JS single-quoted strings containing JSON.
    literal = match.group(1).replace("\\'", "'")
    try:
        payloads.append(json.loads(literal))
    except json.JSONDecodeError:
        continue
candidates = [x for x in payloads if isinstance(x, dict) and {'years', 'days', 'dates'} <= x.keys()]
if len(candidates) != 1:
    raise ValueError("Expected exactly one dates payload")
payload = candidates[0]
days = payload['days']
if type(days) is not int or days <= 0 or not payload['years'] or not isinstance(payload['dates'], dict):
    raise ValueError("Invalid dates payload")
deltas = [0] * days
for category in payload['dates'].values():
    if len(category) != len(payload['years']):
        raise ValueError("Invalid year count")
    for series in category:
        position = 0
        for value in series:
            if type(value) is not int:
                raise ValueError("Non-integer daily value")
            if value < 0:
                position -= value
            else:
                if position >= days:
                    raise ValueError("Daily series exceeds declared length")
                deltas[position] += value
                position += 1
            if position > days:
                raise ValueError("Daily series exceeds declared length")
records = [item for x in payloads if isinstance(x, list) for item in x
           if isinstance(item, dict) and item.get('w') == 'current_total']
if len(records) != 1 or type(records[0].get('real')) is not int:
    raise ValueError("Missing or invalid current_total")
sum_v = records[0]['real']
if not 0 < sum(deltas) <= sum_v:
    raise ValueError("Daily total is inconsistent with current_total")
df = pd.DataFrame({'date': [start_date + timedelta(days=i) for i in range(days)], 'change': deltas})
df['total'] = df['change'].cumsum()
print(f"Validated {days} days, dated total {sum(deltas)}, confirmed total {sum_v}", flush=True)

if not os.path.exists(docs_path):
    os.mkdir(docs_path)

df.to_csv(csv_filename, index=False)
df.to_csv(current_date_csv, index=False)

df.set_index('date', inplace=True)
weekly_sum = df['change'].resample('7D', origin=start_date).sum()

total_casualties = df['change'].sum()

previous_data = df.copy()
current_content = df.reset_index().to_csv(index=False)
for filename in sorted(os.listdir(docs_path), reverse=True):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}_cumsum\.csv', filename):
        continue
    candidate = pd.read_csv(os.path.join(docs_path, filename), parse_dates=['date']).set_index('date')
    if candidate.reset_index().to_csv(index=False) != current_content:
        previous_data = candidate
        print(f"Comparing with {filename}")
        break
previous_weekly_sum = previous_data['change'].resample('7D', origin=start_date).sum()
weekly_sum, previous_weekly_sum = weekly_sum.align(previous_weekly_sum, fill_value=0)
difference = (weekly_sum - previous_weekly_sum).astype(int)

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
