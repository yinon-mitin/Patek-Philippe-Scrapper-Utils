#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import csv
import re
import time
from tqdm import tqdm
from requests.adapters import HTTPAdapter, Retry

# List of allowed base collection URLs
ALLOWED_BASES = [
    '/en/collection/grand-complications',
    '/en/collection/complications',
    '/en/collection/calatrava',
    '/en/collection/gondolo',
    '/en/collection/golden-ellipse',
    '/en/collection/cubitus',
    '/en/collection/nautilus',
    '/en/collection/aquanaut',
    '/en/collection/twenty4',
    '/en/collection/pocket-watches'
]

# Replacement dictionary to fix encoding problems
REPLACEMENTS = {
    "â\x80\x99": "'",
    "â\x80\x98": "'",
    "â\x80\x9D": "\"",
    "â\x80\x9A": ",",
    "â\x80\x94": "—",
    "â\x80\x93": "–",
    "â\x80\xA6": "...",
    "Â": "",
    "â\x80\xA2": "•",
    "oâclock": "o'clock",
    "\u2011": "-",
    "\u0080": "",
    "\u0099": "",
    "×": "x",
    "√â": "x",
    "É": "x",
    "Ã©": "é",
    "Ã¨": "è",
    "Ãª": "ê",
    "Ã«": "ë",
    "Ã®": "î",
    "Ã¯": "ï",
    "Ã´": "ô",
    "Ã¹": "ù",
    "Ã¼": "ü",
    "Ã§": "ç",
    "Ã€": "À",
    "Ã‰": "É",
    "Ãˆ": "È",
    "ÃŠ": "Ê",
    "Ã‹": "Ë",
    "ÃŽ": "Î",
    "Ã": "Ï",
    "Ã\u0094": "Ô",
    "Ã™": "Ù",
    "Ãœ": "Ü",
    "Ã‡": "Ç",
    "â€˜": "'",
    "â€™": "'",
    "â€œ": "\"",
    "â€�": "\"",
    "â€¦": "...",
    "â€": "\"",
    "â": "\"",
    "â": " ",
    "Ï": " ",
    "Ã±": "ñ",
    "â‚¬": "€",
}

def fix_encoding(text):
    # Fixes coding problems and removes extra spaces
    if not text:
        return ""
    # Remove BOM and control characters
    text = text.replace('\ufeff', '')
    # Apply all substitutions
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    # Take out the extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def create_session():
    # Creates a requests session with the desired headers and retrae strategy
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_model_links(session):
    # Gets a list of model URLs from the home page, filtering by allowed collections
    all_models_url = "https://www.patek.com/en/collection/all-models"
    print("Получение списка моделей с главной страницы...")
    response = session.get(all_models_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    links = []
    # Look for all links starting with /en/collection/ and filter by ALLOWED_BASES
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(href.startswith(base) for base in ALLOWED_BASES):
            full_url = "https://www.patek.com" + href
            if full_url not in links:
                links.append(full_url)
    print(f"Найдено {len(links)} ссылок на модели.")
    return links

def parse_watch_page(session, url):
    # Retrieves model data from a given URL
    try:
        response = session.get(url)
    except Exception as e:
        print(f"Ошибка при запросе {url}: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    # SKU extraction
    sku_elem = soup.find(class_="last_element")
    sku = fix_encoding(sku_elem.get_text()) if sku_elem else ""

    # Extract Product subtitle
    subtitle_elem = soup.find(class_="subtitle")
    product_subtitle = fix_encoding(subtitle_elem.get_text()) if subtitle_elem else ""

    # Extract Description
    desc_elem = soup.find("div", class_="article_flexbox_left_content articleDescription")
    description = fix_encoding(desc_elem.get_text()) if desc_elem else ""

    # Extract Collection
    collection_elems = soup.find_all(class_="breadcrumb_link")
    collection = fix_encoding(collection_elems[-1].get_text()) if collection_elems else ""

    # Retrieve watch specifications
    spec_divs = soup.find_all("div", class_="article_flexbox_right_content")
    specs = {}
    for div in spec_divs:
        title_elem = div.find("div", class_="article_flexbox_right_content_title")
        text_elem = div.find("div", class_="article_flexbox_right_content_text")
        if title_elem and text_elem:
            title = fix_encoding(title_elem.get_text()).lower()
            text = fix_encoding(text_elem.get_text())
            specs[title] = text

    watch = specs.get("watch", "")
    dial = specs.get("dial", "")
    case = specs.get("case", "")
    gemsetting = specs.get("gemsetting", "")
    strap = specs.get("strap", "")
    bracelet = specs.get("bracelet", "")
    # Combine Strap and Bracelet into one column
    strap_bracelet = fix_encoding((strap + " " + bracelet).strip()) if (strap or bracelet) else ""

    return {
        "sku": sku,
        "Product subtitle": product_subtitle,
        "description": description,
        "watch": watch,
        "dial": dial,
        "case": case,
        "gemsetting": gemsetting,
        "strap": strap_bracelet,
        "collection": collection,
        "url": url
    }

def main():
    session = create_session()
    model_links = get_model_links(session)

    # Preparing a CSV file
    output_file = "patek_watches.csv"
    fieldnames = ["sku", "Product subtitle", "description", "watch", "dial", "case", "gemsetting", "strap", "collection", "url"]
    records = []

    start_time = time.time()
    # Process models with progress bar display
    for url in tqdm(model_links, desc="Model processing"):
        record = parse_watch_page(session, url)
        if record:
            records.append(record)

    # Writing data to CSV
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)

    elapsed = time.time() - start_time
    print(f"\nScraping complete. Processed {len(records)} models in {elapsed:.2f} seconds.")
    print(f"The data has been saved to a file: {output_file}")

if __name__ == "__main__":
    main()