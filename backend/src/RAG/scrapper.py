from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import time

base_url = "https://www.angelone.in/support"
visited = set()

def crawl(url):
    if url in visited:
        return
    visited.add(url)

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return

        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            href = urljoin(url, link["href"])
            if base_url in href and urlparse(href).scheme in ["http", "https"]:
                crawl(href)

        time.sleep(1)
    except Exception as e:
        print("Error:", e)

crawl(base_url)
urls = list(visited)
print(f"Total pages: {len(urls)}")
