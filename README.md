Patek Philippe Scraper &amp; Data Processor
=======
Patek Philippe Scraper & Data Processor

This repository contains three Python scripts designed to:
	1.	Scrape watch data from the Patek Philippe website.
	2.	Convert / Clean the raw scraped CSV data into a refined format.
	3.	Download watch images for each SKU from the official static domain.

Table of Contents
	•	Prerequisites
	•	Installation
	•	Usage
	•	1. Scraping Data
	•	2. Converting RAW to CSV
	•	3. Downloading Images
	•	Advanced Usage
	•	License

⸻

Prerequisites
	•	Python 3.7+ (Python 3.10+ recommended)
	•	Git (optional, if you want to clone the repository directly)

⸻

Installation
	1.	Clone or Download the Repository

git clone https://github.com/yinon-mitin/Patek-Scraper.git
cd Patek-Scraper

Or download the ZIP from GitHub and unzip into a folder.

	2.	Create and Activate a Virtual Environment (Recommended)
On macOS / Linux:

python3 -m venv venv
source venv/bin/activate

On Windows:

python -m venv venv
venv\Scripts\activate


	3.	Install Dependencies

pip install -r requirements.txt



That’s it! You’re now ready to run the scripts.

⸻

Usage

1. Scraping Data

Use 1-Patek_Scrapper.py to scrape watch data from the Patek Philippe website.
This script connects to the official site, navigates the collections, extracts watch details, and writes the data to a CSV.

python 1-Patek_Scrapper.py

Output:
	•	patek_watches.csv in the same directory.
Each row represents a watch with columns like SKU, Product Subtitle, Description, Case, Dial, Strap, etc.

Notes:
	•	The script may take some time depending on connection speed and the total number of watches.
	•	It retries requests automatically to handle transient network errors.

2. Converting RAW to CSV

After you’ve obtained patek_watches.csv, run 2-RAWtoCSV.py to further clean, parse, and transform the data fields.

Usage:

python 2-RAWtoCSV.py -i patek_watches.csv

Optional Parameters:
	•	-o OUTPUT_BASENAME
By default, it will produce <input_file>_final.csv and <input_file>_final.xlsx.
If you specify -o mydata, it will produce mydata.csv and mydata.xlsx.

Output:
	•	A new CSV and XLSX file with additional columns: Title, Ref Number, Material, Movement Type, etc.

3. Downloading Images

Finally, use 3-Patek_Image_Downloader.py to grab watch images from the Patek servers.

python 3-Patek_Image_Downloader.py

How It Works:
	•	It fetches the SKU list from the “all-models” page.
	•	For each SKU, it attempts to download up to MAX_IMAGE_NUMBER images using a known file naming pattern.
	•	By default, images are saved into img/ folder under filenames like PP-<SKU>-<num>.jpg.

Output:
	•	An img folder containing the downloaded images.
	•	Progress is displayed via a progress bar, showing how many images have been successfully fetched.

⸻

Advanced Usage
	•	Adjust MAX_IMAGE_NUMBER in 3-Patek_Image_Downloader.py if you expect more or fewer images per watch.
	•	Edit the collection list in 1-Patek_Scrapper.py (ALLOWED_BASES) if you want to include / exclude certain collections.
	•	Check the replacement dictionary in 1-Patek_Scrapper.py if you notice any odd characters in the scraped text. Extend or modify as needed.
	•	The 2-RAWtoCSV.py script includes various parsing functions (case diameter, strap color, water resistance, movement type, etc.). Tweak or enhance these if the site’s markup or naming conventions change.

⸻

License

This project is released under the MIT License. You are free to use, modify, and distribute it as you wish.

⸻

Enjoy scraping and data processing! If you encounter any issues, feel free to open an Issue or submit a Pull Request.
