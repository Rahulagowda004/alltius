from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import time
import random
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from collections import deque
import os
import re
import json
from datetime import datetime
from urllib.parse import unquote

base_url = "https://www.angelone.in/support"
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
]

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crawled_data")
RAG_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_data")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_HEADING_LEVEL = 3

EXCLUDED_PATHS = [
    "/hindi",
]

def should_crawl_url(url):
    parsed = urlparse(url)
    
    for excluded_path in EXCLUDED_PATHS:
        if excluded_path in parsed.path:
            return False
    
    if base_url in url and parsed.scheme in ["http", "https"]:
        return True
    
    return False

def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=2,
        respect_retry_after_header=True
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': base_url,
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

def sanitize_filename(url):
    path = urlparse(url).path
    fragment = urlparse(url).fragment
    if fragment:
        path = f"{path}#{fragment}"
    path = unquote(path)
    filename = re.sub(r'[\\/*?:"<>|]', '_', path)
    filename = filename.strip('/')
    if not filename:
        return 'index'
    if len(filename) > 200:
        filename = filename[:200]
    return filename + '.html'

def extract_structured_content(soup):
    for element in soup.select('nav, footer, header, .navigation, .menu, .footer, .header, .sidebar, script, style, iframe'):
        element.extract()
    title = soup.title.string if soup.title else "No Title"
    title = title.strip()
    main_content = soup.select_one('main, article, .content, .main, #content, #main')
    if not main_content:
        main_content = soup
    structured_content = {
        "title": title,
        "headings": [],
        "paragraphs": [],
        "sections": []
    }
    for i in range(1, MAX_HEADING_LEVEL + 1):
        for heading in main_content.find_all(f'h{i}'):
            structured_content["headings"].append({
                "level": i,
                "text": heading.get_text().strip()
            })
    for p in main_content.find_all('p'):
        text = p.get_text().strip()
        if text:
            structured_content["paragraphs"].append(text)
    current_section = {"heading": "", "content": ""}
    for element in main_content.find_all(['h1', 'h2', 'h3', 'p']):
        if element.name.startswith('h'):
            if current_section["heading"] and current_section["content"].strip():
                structured_content["sections"].append(current_section.copy())
            current_section = {
                "heading": element.get_text().strip(),
                "content": ""
            }
        elif element.name == 'p':
            current_section["content"] += element.get_text().strip() + "\n\n"
    if current_section["heading"] and current_section["content"].strip():
        structured_content["sections"].append(current_section)
    full_text = extract_text_content(main_content)
    structured_content["full_text"] = full_text
    structured_content["chunks"] = create_text_chunks(full_text, CHUNK_SIZE, CHUNK_OVERLAP)
    return structured_content

def create_text_chunks(text, chunk_size, chunk_overlap):
    if not text:
        return [] 
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length:
            for i in range(min(50, chunk_size)):
                if end - i > start and text[end - i] in ['.', '!', '?', '\n'] and (end - i + 1 >= text_length or text[end - i + 1].isspace()):
                    end = end - i + 1
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - chunk_overlap if end < text_length else text_length
    return chunks

def extract_text_content(soup):
    for script_or_style in soup(["script", "style"]):
        script_or_style.extract()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

def save_page(url, html_content, soup):
    for directory in [DATA_DIR, RAG_DATA_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)
    filename = sanitize_filename(url)
    html_filepath = os.path.join(DATA_DIR, filename)
    rag_filepath = os.path.join(RAG_DATA_DIR, filename.replace('.html', '.json'))
    title = soup.title.string if soup.title else "No Title"
    structured_content = extract_structured_content(soup)
    metadata = {
        "url": url,
        "title": title.strip(),
        "crawled_at": datetime.now().isoformat(),
        "content_type": "text/html",
        "source": "Angel One Support",
        "num_chunks": len(structured_content["chunks"])
    }
    with open(html_filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    rag_data = {
        "metadata": metadata,
        "structured_content": structured_content
    }
    with open(rag_filepath, 'w', encoding='utf-8') as f:
        json.dump(rag_data, f, ensure_ascii=False, indent=2)
    return True

def crawl_iterative():
    session = create_session()
    visited = set()
    to_visit = deque([base_url])
    pages_saved = 0
    while to_visit:
        url = to_visit.popleft()
        if url in visited:
            continue
        visited.add(url)
        print(f"Crawling {url} ({len(visited)} visited, {len(to_visit)} queued)")
        try:
            response = session.get(url, headers=get_random_headers(), timeout=30)
            if response.status_code != 200:
                print(f"Failed to fetch {url}: Status code {response.status_code}")
                continue
            html_content = response.text
            soup = BeautifulSoup(html_content, "html.parser")
            if save_page(url, html_content, soup):
                pages_saved += 1
            for link in soup.find_all("a", href=True):
                href = urljoin(url, link["href"])
                if should_crawl_url(href):
                    to_visit.append(href)
                    print(f"Queued {href} for crawling")
            delay = 1 + random.random() * 2
            time.sleep(delay)
        except requests.exceptions.Timeout:
            print(f"Timeout occurred while fetching {url}")
        except requests.exceptions.ConnectionError:
            print(f"Connection error while fetching {url}")
        except Exception as e:
            print(f"Error while crawling {url}: {str(e)}")
    
    return visited, pages_saved

if __name__ == "__main__":
    for directory in [DATA_DIR, RAG_DATA_DIR]:
        if os.path.exists(directory):
            import shutil
            try:
                shutil.rmtree(directory)
            except Exception as e:
                print(f"Error while clearing data from {directory}: {str(e)}")
    start_time = time.time()
    
    visited_urls, num_pages_saved = crawl_iterative()
    
    elapsed_time = time.time() - start_time
    
    print(f"Crawling completed in {elapsed_time:.2f} seconds")
    print(f"Total pages visited: {len(visited_urls)}")
    print(f"Total pages saved: {num_pages_saved}")
    
    sample = list(visited_urls)[:5]
    for i, url in enumerate(sample, 1):
        print(f"URL {i}: {url}")
