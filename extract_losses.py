import httpx
import re

mz_page = 'https://zona.media/casualties'
headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html",
    "Accept-Encoding": "gzip",
    "Accept-Language": "en-GB",
    "Connection": "keep-alive",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Host": "zona.media",
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
        print('js is found')  
        response = client.get(url_js, headers=headers)      
        js = response.text
        print(js)
    else:
        print(f"Error loading page: {response.status_code}")
except:
    print('Connection error')
