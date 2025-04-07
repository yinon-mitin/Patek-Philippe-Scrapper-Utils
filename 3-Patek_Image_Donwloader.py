#!/usr/bin/env python3
import os
import time
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from requests.adapters import HTTPAdapter, Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
ALL_MODELS_URL = "https://www.patek.com/en/collection/all-models"
IMAGE_BASE_URL = "https://static.patek.com/images/articles/gallery/2200/"
IMG_FOLDER = "img"
MAX_IMAGE_NUMBER = 21

def create_session():
    # Creates a session with the desired headers and retrace strategy.
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_skus(session):
    
    # Goes to the all-models page and retrieves the SKU list.
    # The SKU is taken from the last segment of the URL if it contains a '-' character.
    
    print("Получение списка моделей со страницы all-models...")
    response = session.get(ALL_MODELS_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    skus = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/en/collection/") and "all-models" not in href:
            candidate = href.rstrip("/").split("/")[-1]
            if "-" in candidate:
                skus.add(candidate)
    skus = list(skus)
    print(f"Найдено {len(skus)} моделей (SKU).")
    return skus

def download_image(session, sku, num):
    
    # Forms the URL of the image using the pattern and tries to download it with a timeout of 3 sec.
    # If the server returns HTTP 200, the image is saved to the IMG_FOLDER folder under the name:
    # PP-(SKU)-(num).jpg
    
    sku_formatted = sku.replace("-", "_")
    image_url = f"{IMAGE_BASE_URL}{sku_formatted}_{num}@2x.jpg"
    filename = f"PP-{sku}-{num}.jpg"
    filepath = os.path.join(IMG_FOLDER, filename)
    try:
        response = session.get(image_url, stream=True, timeout=3)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception:
        pass
    return False

def main():
    start_time = time.time()

    # Create a folder for images if it does not exist
    if not os.path.exists(IMG_FOLDER):
        os.makedirs(IMG_FOLDER)

    session = create_session()
    skus = get_skus(session)

    total_images = 0
    tasks = []

    # Form download tasks: for each SKU and number from 1 to MAX_IMAGE_NUMBER
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for sku in skus:
            for num in range(1, MAX_IMAGE_NUMBER + 1):
                futures.append(executor.submit(download_image, session, sku, num))
        # Tracking progress through tqdm
        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading images"):
            if future.result():
                total_images += 1

    elapsed = time.time() - start_time
    print(f"\nProcessing completed in {elapsed:.2f} seconds.")
    print(f"Processed models: {len(skus)}")
    print(f"Downloaded images: {total_images}")

if __name__ == "__main__":
    main()