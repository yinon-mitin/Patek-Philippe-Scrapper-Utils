Patek Philippe Scraper &amp; Data Processor
=======
Patek Philippe Scraper & Data Processor

This repository contains three Python scripts designed to:

1.	Scrape watch data from the Patek Philippe website.
2.	Convert / Clean the raw scraped CSV data into a refined format.
3.	Download watch images for each SKU from the official static domain.



# Prerequisites

​• Python 3.7+ (Python 3.10+ recommended) 

• Git (optional, if you want to clone the repository directly)



# Installation
### 1. Clone or Download the Repository

``` bash
git clone https://github.com/yinon-mitin/Patek-Philippe-Scrapper-Utils.git
cd Patek-Scraper
```

Or download the ZIP from GitHub and unzip into a folder.

### 2. Create and Activate a Virtual Environment (Recommended)

On macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows:

```bash
python -m venv venv
source venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip3 install -r requirements.txt
```

That’s it! You’re now ready to run the scripts.



# Usage

### 1. Scraping Data

Use <u>1-Patek_Scrapper.py</u> to scrape watch data from the Patek Philippe website.

This script connects to the official site, navigates the collections, extracts watch details, and writes the data to a CSV.

```bash
python3 1-Patek_Scrapper.py
```

Output:

​	•	<u>patek_watches.csv</u> in the same directory.

  Each row represents a watch with columns like SKU, Product Subtitle, Description, Case, Dial, Strap, etc.

Notes:

​	•	The script may take some time depending on connection speed and the total number of watches.

  •	It retries requests automatically to handle transient network errors.

### 2. Converting RAW to CSV

After you’ve obtained <u>patek_watches.csv</u>, run <u>2-RAWtoCSV.py</u> to further clean, parse, and transform the data fields.

Usage:

```bash
python3 2-RAWtoCSV.py -i patek_watches.csv
```

Optional Parameters:

​	•	`-o` OUTPUT_NAME

  By default, it will produce *<input_file>_final.csv* and *<input_file>_final.xlsx*.
​	If you specify `-o mydata`, it will produce <u>mydata.csv</u> and <u>mydata.xlsx</u>.

Output:

​	•	A new CSV and XLSX file with additional columns: Title, Ref Number, Material, Movement Type, etc.

### 3. Downloading Images

Finally, use <u>3-Patek_Image_Downloader.py</u> to grab watch images from the Patek servers.

```bash
python3 3-Patek_Image_Downloader.py
```

How It Works:

​	•	It fetches the SKU list from the “all-models” page.

  •	For each SKU, it attempts to download up to MAX_IMAGE_NUMBER images using a known file naming pattern.
  
  •	By default, images are saved into img/ folder under filenames like *PP-SKU-num.jpg*.

Output:

​	•	An img folder containing the downloaded images.
​	
  •	Progress is displayed via a progress bar, showing how many images have been successfully fetched.



# Advanced Usage

​	•	Edit the collection list in <u>1-Patek_Scrapper.py</u> (ALLOWED_BASES) if you want to include / exclude certain collections.

​	•	Check the replacement dictionary in <u>1-Patek_Scrapper.py</u> if you notice any odd characters in the scraped text. Extend or modify as needed.

  •	The <u>2-RAWtoCSV.py</u> script includes various parsing functions (case diameter, strap color, water resistance, movement type, etc.). Tweak or enhance these if the site’s markup or naming conventions change.
  
  •	Adjust MAX_IMAGE_NUMBER in <u>3-Patek_Image_Downloader.py</u> if you expect more or fewer images per watch.



# License

This project is released under the MIT License. You are free to use, modify, and distribute it as you wish.

------

Enjoy scraping and data processing! If you encounter any issues, feel free to open an Issue or submit a Pull Request.
