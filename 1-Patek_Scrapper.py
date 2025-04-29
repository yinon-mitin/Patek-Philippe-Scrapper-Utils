#!/usr/bin/env python3
import requests
import json
import os
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
    print("Getting a list of models from the home page...")
    response = session.get(all_models_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    links = []
    # Look for all links starting with /en/collection/ and filter by ALLOWED_BASES
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(href.startswith(base) for base in ALLOWED_BASES):
            # Make sure this is a model page and not a collection page
            if href.count('/') > 3:  # /en/collection/nautilus/5711-1A-010
                full_url = "https://www.patek.com" + href
                if full_url not in links:
                    links.append(full_url)
    
    print(f"Found {len(links)} of links to models.")
    return links

def safe_extract(pattern, text, group=1, default=""):
    """Safely extract regex matches with error handling"""
    try:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            # Try each capture group from 1 to 3 (our patterns can have multiple capture options)
            for i in range(1, 4):
                try:
                    value = match.group(i)
                    if value and value.strip():
                        return fix_encoding(value.strip())
                except (IndexError, AttributeError):
                    continue
        return default
    except Exception as e:
        if 'DEBUG' in os.environ:
            print(f"[⚠️] Regex extraction error: {e}")
        return default

def extract_datalayer_info(soup) -> dict:
    """
    Extracts key metadata (collection, gender, movementType) from the last dataLayer script.
    Handles malformed JavaScript-style formatting with regex.
    """
    scripts = soup.find_all("script")
    for script in scripts:
        if "dataLayer" not in script.text:
            continue

        matches = re.findall(r"dataLayer\s*=\s*\[\s*({.*?})\s*];", script.text, re.DOTALL)
        if not matches:
            continue

        data_str = matches[-1]  # take the last (most complete) match

        # Clean JS-style object for regex parsing
        data_str = data_str.replace("'", '"')
        data_str = re.sub(r",\s*}", "}", data_str)
        data_str = data_str.replace("\\", "\\\\")

        def extract(field):
            pattern = rf'"{field}"\s*:\s*"([^"]+)"'
            match = re.search(pattern, data_str)
            return fix_encoding(match.group(1)) if match else ""

        return {
            "collection": extract("collection"),
            "gender": extract("gender"),
            "movementType": extract("movementType"),
        }

    return {}

def parse_watch_page(session, url):
    """
    Parses detailed watch data from a product page.
    Extracts SKU, title, description, specs, and structured metadata.
    """
    try:
        response = session.get(url)
    except Exception as e:
        print(f"[Error] Request failed: {url} | {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')


    # Extract structured metadata from dataLayer (in silent mode)
    datalayer = extract_datalayer_info(soup)

    # Extract SKU from element with class 'last_element'
    sku_elem = soup.find(class_="last_element")
    sku = fix_encoding(sku_elem.get_text()) if sku_elem else datalayer.get("article", "")
    # Extract Description
    desc_elem = soup.find("div", class_="article_flexbox_left_content articleDescription")
    description = fix_encoding(desc_elem.get_text()) if desc_elem else ""

    # Fallback collection from breadcrumb (if dataLayer fails)
    collection = fix_encoding(datalayer.get("collection", ""))
    if not collection:
        collection_elems = soup.find_all(class_="breadcrumb_link")
        collection = fix_encoding(collection_elems[-1].get_text()) if collection_elems else ""

    # Gender and movementType from dataLayer
    gender = fix_encoding(datalayer.get("gender", ""))
    movement_type = fix_encoding(datalayer.get("movementType", ""))

    # Case shape and material from dataLayer
    case_shape = fix_encoding(datalayer.get("caseShape", ""))
    material = fix_encoding(datalayer.get("material", ""))
    complications = fix_encoding(datalayer.get("complications", ""))

    # Extract Caliber and product subtitle from <div class="attributes">
    attributes_div = soup.find("div", class_="attributes")
    caliber = ""
    product_subtitle = ""
    if attributes_div:
        reference_span = attributes_div.find("span", class_="reference")
        if reference_span:
            caliber = fix_encoding(reference_span.get_text())
        paragraph = attributes_div.find("p")
        if paragraph:
            raw_html = str(paragraph)
            split_html = raw_html.split("<strong>", 1)[0]
            product_subtitle = fix_encoding(BeautifulSoup(split_html, "html.parser").get_text())

    # Extract watch specifications from right content blocks
    specs = {}
    spec_divs = soup.find_all("div", class_="article_flexbox_right_content")
    for div in spec_divs:
        title_elem = div.find("div", class_="article_flexbox_right_content_title")
        text_elem = div.find("div", class_="article_flexbox_right_content_text")
        if title_elem and text_elem:
            title = fix_encoding(title_elem.get_text()).lower()
            text = fix_encoding(text_elem.get_text())
            specs[title] = text

    # Extract individual spec values
    watch = specs.get("watch", "")
    dial = specs.get("dial", "")
    case = specs.get("case", "")
    gemsetting = specs.get("gemsetting", "")
    strap = specs.get("strap", "")
    bracelet = specs.get("bracelet", "")
    strap_bracelet = fix_encoding((strap + " " + bracelet).strip()) if (strap or bracelet) else ""

    # Final data dictionary
    return {
        "sku": sku,
        "Product subtitle": product_subtitle,
        "description": description,
        "caliber": caliber,
        "watch": watch,
        "dial": dial,
        "case": case,
        "gemsetting": gemsetting,
        "strap": strap_bracelet,
        "collection": collection,
        "gender": gender,
        "movement_type": movement_type,
        "url": url
    }

def main():
    session = create_session()
    model_links = get_model_links(session)

    # Preparing output CSV
    output_file = "patek_watches.csv"
    fieldnames = [
        "sku",
        "Product subtitle",
        "description",
        "caliber",
        "watch",
        "dial",
        "case",
        "gemsetting",
        "strap",
        "collection",
        "gender",
        "movement_type",
        "url"
    ]
    records = []

    start_time = time.time()
    for url in tqdm(model_links, desc="Model processing"):
        record = parse_watch_page(session, url)
        if record:
            records.append(record)

    # Save to CSV
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