import httpx
import re

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
}

url_pattern = r'https://[a-zA-Z0-9.-]*/infographics/bodycount/[a-zA-Z0-9.-]*\.js\.gz'



try:
    client = httpx.Client(http2=True)

    # Выполняем запрос
    response = client.get(mz_page, headers=headers)
    if response.status_code == 200:
        # Получаем содержимое страницы
        page_content = response.text
        js_gz_urls = re.findall(url_pattern, page_content)
        url_js = js_gz_urls[0] if js_gz_urls else "URL is not found"
        print(url_js)        
    else:
        print(f"Error loading page: {response.status_code}")
except:
    print('Connection error')
