#!/usr/bin/env python3
import pandas as pd
import re
import os
import html
import argparse


def clean_text(text: str) -> str:
    # Remove HTML tags, spaces, HTML entities.
    if not text or pd.isna(text):
        return ""
    text = html.unescape(text).strip()              # &amp; → &
    text = re.sub(r"<[^>]*>", "", text)             # удаляем теги
    return text.strip()

# === Parsing Case (Material, Dimensions, Crystal) ===

def parse_case_material(case_text: str) -> str:
    
    # Look for mentions of Steel, Stainless Steel, White Gold, Rose Gold, Yellow Gold, Platinum.
    # Consider that 'Stainless Steel' takes precedence over 'Steel' (if 'stainless steel' appears in the text, 
    # then it is 'Stainless Steel', not just 'Steel').
    
    text_lower = case_text.lower()
    # The order is important: if it says “stainless steel”, we don't want to match just steel
    if "stainless steel" in text_lower:
        return "Stainless Steel"
    elif "steel" in text_lower:
        return "Steel"
    elif "white gold" in text_lower:
        return "White Gold"
    elif "rose gold" in text_lower:
        return "Rose Gold"
    elif "yellow gold" in text_lower:
        return "Yellow Gold"
    elif "platinum" in text_lower:
        return "Platinum"
    return ""

def parse_case_diameter(case_text: str) -> str:
    
    # Searches for the diameter of the watch using the following options:
    #   - “Diameter: 38 mm”
    #   - “Case diameter: 40.5 mm”
    #   - “Diameter (10'4 o'clock): 38.8 mm”
    #   - “Case diameter (10-4 o'clock): 40.8 mm”
    # Returns the numeric value as a string (e.g. “38.8”) or “” if not found.
    
    pattern = (
        r"(?:[Cc]ase\s+)?[Dd]iameter"         # “Case diameter” or “Diameter”
        r"(?:\s*\([^)]*\))?"                  # Optional block in brackets, e.g. (10'4 o'clock)
        r"\s*:\s*"                           # Colon with spaces
        r"(\d+(?:\.\d+)?)"                   # Numeric value (integer or fractional)
        r"(?:[\s\u00A0\u2009]*mm\.?)"         # “mm” with spaces (including normal, unbroken and thin spaces) and a possible period
    )
    match = re.search(pattern, case_text)
    return match.group(1).strip() if match else ""

def parse_case_dimensions(case_text: str) -> str:
    
    # Searches the dimensions string for the following options:
    # - “Case dimensions: 25.1 x 30 mm.”
    # - “Dimensions: 28.6 x 40.85 mm. Height: 7.36 mm.”
    # Returns the entire sequence of characters that begins after “dimensions:” (or “dimensions:”),
    # including numbers, spaces, the “x” (or “×”) separator, hyphens, etc., up to “mm”.
    # For example, for the string “Dimensions: 28.6 x 40.85 mm. Height: 7.36 mm.” the function will return “28.6 x 40.85 mm”.
    
    pattern = (
        r"(?:[Cc]ase\s+)?[Dd]imension(?:s)?\s*:\s*"  # "Case dimensions:" or "Dimensions:" (s optonally)
        r"([\d\.,\s×x\-–Éé]+mm)"                     # All characters allowed in the size up to “mm”
    )
    match = re.search(pattern, case_text)
    return match.group(1).strip() if match else ""

def parse_case_height(case_text: str) -> str:
    
    # Extracts the height or thickness of the watch case from the text.
    # 
    # Supported options:
    # - “Height : 16.32 mm”
    # - “Height : 16.32 mm”
    # - “Height: 16.32 mm” (in case of a typo)
    # - “Thickness : 7.36 mm”
    # - “Thickness : 7.36 mm”
    # 
    # Returns a numeric value (e.g. “16.32” or “7.36”) or an empty string if not found.
    
    pattern = r"(?:[Hh](?:eight|ight)|[Tt]hickness)\s*:\s*(\d+(?:\.\d+)?)\s*mm"
    match = re.search(pattern, case_text)
    return match.group(1).strip() if match else ""

def build_size_dimensions(case_text: str, diameter_val: str) -> str:
    
    # Returns the value for the “Size/Dimensions” column in the format:
    # - “xx.x mm x yy.y mm” if both diameter and height/thickness are found
    # - “xx.x mm” if only diameter is found
    # - If there is no diameter data in the case, returns an empty string.
    # 
    # If dimensions are explicitly present in the text (e.g., “Case dimensions: ...”),
    # the function uses them in their entirety. Otherwise, it assembles the string from diameter and height/thickness.
    
    # If explicit dimensions are present, we use them:
    dims = parse_case_dimensions(case_text)
    if dims:
        return dims.strip()

    # Try to extract height/thickness:
    height_val = parse_case_height(case_text)
    
    # Convert the extracted values to a format with one decimal digit,
    # if they exist and are correctly converted to a number.
    try:
        if diameter_val:
            diameter_num = float(diameter_val)
            diameter_formatted = f"{diameter_num:.1f}"
        else:
            diameter_formatted = ""
    except ValueError:
        diameter_formatted = diameter_val

    try:
        if height_val:
            height_num = float(height_val)
            height_formatted = f"{height_num:.1f}"
        else:
            height_formatted = ""
    except ValueError:
        height_formatted = height_val

    if diameter_formatted and height_formatted:
        return f"{diameter_formatted} mm x {height_formatted} mm"
    elif diameter_formatted:
        return f"{diameter_formatted} mm"
    else:
        return ""

def parse_crystal(case_text: str) -> str:
    
    # Look for mention of Sapphire crystal, Solid case back etc.
    # Return the last mention. If not, empty.
    
    text_lower = case_text.lower()
    pattern = r"(sapphire crystal case back|sapphire crystal|solid case back)"
    candidates = list(re.finditer(pattern, text_lower))
    if candidates:
        last_val = candidates[-1].group(1)
        return last_val.title()
    return ""

def parse_water_resistance(case_text: str) -> str:
    
    # 1) If 'not water-resistant' occurs (any case) 
    # => return 'Not Water-resistant'.
    # 2) If 'water-resistant to X m' is encountered (including 'meters'), 
    # => return 'Xm', e.g. '30m'.
    # 3) Otherwise return ''.
    
    text_lower = case_text.lower()
    
    # 1) Check for “not water-resistant”
    not_water_pattern = r"not\s*\(?water(?:[\s\-])?resistant\)?"
    if re.search(not_water_pattern, text_lower):
        return "Not Water-resistant"

    # 2) If not, look for “water-resistant to 30 m”, “water resistant to 30.5 meters”, etc.
    # Allow either a space or hyphen between 'water' and 'resistant'
    pattern = r"[Ww]ater(?:[\s\-])?resistant\s*to\s*(\d+(?:\.\d+)?)(?:\s*m(?:eters)?)"
    match = re.search(pattern, case_text)
    if match:
        number_str = match.group(1)  # e.g. '30' or '30.5'
        return number_str + "m"
    
    # 3) If nothing found, blank
    return ""


# === Parsing Strap (Type, Color, Buckle) ===

def parse_strap_type(strap_text: str) -> str:
    
    # Look for Steel bracelet, Alligator leather, etc. 
    # You can extend the logic: if you see “steel bracelet” => “Steel bracelet”.
    # If “stainless steel bracelet” => “Stainless Steel bracelet”.
    
    # First fragment before comma or period
    first_part = re.split(r"[,\.]", strap_text, maxsplit=1)[0].strip().lower()

    # Substitution: if there is “steel bracelet” => “Steel bracelet”
    # (or “Stainless Steel bracelet”), etc.
    # If there is “alligator” => “Alligator Leather” (example)
    if "alligator" in first_part:
        return "Alligator Leather"
    if "calfskin" in first_part:
        return "Calfskin"
    if "Steel" in first_part:
        return "Stainless Steel"
    if "steel" in first_part:
        return "Stainless Steel"
    if "rose gold" in first_part:
        return "Rose Gold"
    if "white gold" in first_part:
        return "White Gold"
    if "composite" in first_part:
        return "Composite material"
    if "polymer" in first_part:
        return "Polymer"
    if "pearls (~48.85 ct) and white gold" in first_part:
        return "White Gold and Pearls"
    if "pearls (~48.85 ct) and rose gold" in first_part:
        return "Rose Gold and Pearls"
    if "pearls (~48.85 ct) and yellow gold" in first_part:
        return "Yellow Gold and Pearls"
    # If there's nothing, we'll return it while it's empty #
    return ""

def parse_strap_color(strap_text: str) -> str:
    
    # Search the first sentence for words from the list (blue, black...) 
    # Taking into account the word boundaries (\bblue\b).
    # We take the last match we find.
    # Also note that “lacquered” doesn't give us “red”.
    
    color_list = [
        "navy blue", "blue", "black", "brown", "dark brown", "gray", "grey",
        "green", "beige", "red", "olive green", "purple", "blue-gray", 
        "white", "stainless steel", "rose gold", "yellow gold", "white gold",
        "blue-green", "chestnut", "steel", "taupe"
    ]
    # We'll just take the first sentence
    first_sentence = re.split(r"\.", strap_text, maxsplit=1)[0].lower()
    found_colors = []

    for color in color_list:
        # Make a pattern like r“\bnavy\s+blue\b” for two-word, or r"\bblue\b”
        escaped = re.escape(color)  # Escape to make spaces and hyphens work
        pattern = rf"\b{escaped}\b"
        if re.search(pattern, first_sentence):
            found_colors.append(color)

    if found_colors:
        # Take the last match
        last_color = found_colors[-1]
        # Do “Navy Blue” or “Blue-Green” (capitalize each word)
        return " ".join([w.capitalize() for w in last_color.split()])
    return ""


def parse_buckle(strap_text: str) -> str:
    # Last mention 'fold-over clasp', 'folding clasp', 'prong buckle', 'buckle', 'clasp'.
    text_lower = strap_text.lower()
    pattern = r"(fold-over clasp|folding clasp|prong buckle|buckle|clasp)"
    candidates = list(re.finditer(pattern, text_lower))
    if not candidates:
        return ""
    last_val = candidates[-1].group(1)
    if last_val == "fold-over clasp":
        return "Fold-over Clasp"
    if last_val == "folding clasp":
        return "Folding Clasp"
    if last_val == "prong buckle":
        return "Prong Buckle"
    if last_val == "buckle":
        return "Buckle"
    if last_val == "clasp":
        return "Clasp"
    return ""


# === Parsing Dial (color, diamonds) ===

def parse_dial_color(dial_text: str) -> str:
    
    # Look for the last occurrence from the list (white, black, blue...) taking into account the word boundaries:
    # \bblue\b, etc. so that 'lacquered' does not give 'red'.
    
    color_candidates = [
        "white", "beige", "mother of pearl", "green", "olive green", "blue",
        "black", "red", "gray", "brown", "purple", "chestnut", "multicolored", 
        "portion of the sky", "ivory", "taupe", "silvery", "milky way", "rose-gilt", 
        "diamonds"
    ]
    dial_lower = dial_text.lower()
    found_colors = []
    for c in color_candidates:
        escaped = re.escape(c)
        pattern = rf"\b{escaped}\b"
        if re.search(pattern, dial_lower):
            found_colors.append(c)
    if found_colors:
        last_color = found_colors[-1]
        # Lead to “Black”, “Mother Of Pearl”, etc.
        return " ".join(word.capitalize() for word in last_color.split())
    return ""


# === Other (Gender, Movement, Diamonds...) ===

def parse_watch_shape(collection_name: str) -> str:
    
    # Complications collection names => shape:
    # Grand Complications, Complications, Calatrava, Twenty~4, Pocket Watches => Round
    # Gondolo => Rectangular
    # Golden Ellipse => Elipse
    # Nautilus, Aquanaut => Octagon
    # Cubitus => Square
    # If unknown, empty.
    
    name = collection_name.lower().replace("-", " ").strip()
    shape_map = {
        "grand complications": "Round",
        "complications": "Round",
        "calatrava": "Round",
        "twenty4": "Round",
        "pocket watches": "Round",
        "gondolo": "Rectangular",
        "golden ellipse": "Elipse",
        "nautilus": "Octagon",
        "aquanaut": "Octagon",
        "cubitus": "Square"
    }
    return shape_map.get(name, "")

def parse_movement_type(watch: str, watch_movement: str) -> str:
    
    # If watch_type contains 'automatic'/'manual'/'quartz', return this.
    # Otherwise, check watch_movement for 'self-winding' (-> automatic), 'manual', 'quartz'.
    
    wt = watch.lower()
    if "automatic" in wt or "self-winding" in wt:
        return "Automatic"
    if "manual" in wt or "hand-wound" in wt:
        return "Manual"
    if "quartz" in wt:
        return "Quartz"

    wm = watch_movement.lower()
    if "automatic" in wm or "self-winding" in wm:
        return "Automatic"
    if "manual" in wm or "hand-wound" in wm:
        return "Manual"
    if "quartz" in wm:
        return "Quartz"

    return ""

def determine_gender_by_size(diameter_str: str) -> (str, str):
    
    # Determines values for Gender and Gender New based on Case Size (diameter).
    # 
    # Argument:
    # diameter_str: extracted diameter (e.g., “40.5”)
    # 
    # Returns:
    # (gender, gender_new)
    # - If diameter is less than 36 mm: (“For Her”, “Ladies”)
    # - If the diameter is 38 mm or more: (“For Him, For Her”, “Gents”)
    # - If the diameter is between 36 and 38 mm: (“For Him, For Her”, “Gents”) (the threshold can be changed)
    
    try:
        d = float(diameter_str)
    except (ValueError, TypeError):
        # If it fails to convert, default to male
        return ("For Him, For Her", "Gents")
    
    if d < 36:
        return ("For Her", "Ladies")
    elif d >= 38:
        return ("For Him, For Her", "Gents, Ladies")
    else:
        # For intermediate values (36-38 mm) default to male orientation
        return ("For Him, For Her", "Gents, Ladies")

def parse_gemsetting_info(gem_text: str) -> (str, str):
    
    # Accepts gem_text (from the 'gemsetting' field or other description).
    # Returns a tuple (gemstones, gemsetting_description) where:
    # 1) gemstones: 'Yes' if the text mentions gemstones, otherwise 'No';
    # 2) gemsetting_description: either the description text itself or ''.
    
    gem_text = gem_text.strip()
    if gem_text:
        # If it's not empty, we think there are stones
        return ('Yes', gem_text)
    else:
        # Otherwise write that no
        return ('No', '')

def remove_sku_suffix(sku: str) -> str:
    
    # Remove suffixes like '-001' from SKUs.
    # Example: 5327G-001 -> 5327G

    match = re.match(r"^(.*?)\-\d+$", sku.strip())
    if match:
        return match.group(1)
    return sku

def build_product_subtitle(sku: str, collection_title: str) -> str:
    
    # By convention: 'SKU without suffixes' + '-' + {Collection titlecase}
    
    base = remove_sku_suffix(sku)
    return f"{base}-{collection_title}"

# =============================
# Basic script 
# =============================

def main():
    parser = argparse.ArgumentParser(description="Process CSV file for Patek Philippe data.")
    parser.add_argument("-i", "--input", required=True, help="Input CSV file name")
    parser.add_argument("-o", "--output", help="Output file base name (without extension)")
    args = parser.parse_args()

    input_file = args.input
    # If no output base file is specified, generate it by appending _final to the input file base name
    if args.output:
        output_base = args.output
    else:
        base, _ = os.path.splitext(input_file)
        output_base = base + "_final"

    # Read CSV from the file specified by the -i flag
    df = pd.read_csv(args.input, dtype=str, encoding="utf-8")
    
    # Further processing...
    print("Файл успешно прочитан:", args.input)

    # List of output columns
    out_cols = [
        "Title",
        "Product Subtitle",
        "Description",
        "Short Description",
        "Collection",
        "Collection Description",
        "Model",
        "Ref Number",
        "Brands",
        "Type",
        "Material",
        "Case Material",
        "Strap Type",
        "Strap Color",
        "Dial Color",
        "Case Size(mm)",
        "Size/Dimensions",
        "Case Height",
        "Water Resistance",
        "Gender",
        "Gender New",
        "Buckle",
        "Crystal",
        "Movement Type",
        "Watch Shape",
        "Gemstones",
        "Gemstones Description",
        "Call for Price",
        "URL"
    ]

    results = []

    for _, row in df.iterrows():
        sku_raw = clean_text(row.get("sku", ""))
        desc = clean_text(row.get("description", ""))
        case_text = clean_text(row.get("case", ""))
        strap_text = clean_text(row.get("strap", ""))
        dial_text = clean_text(row.get("dial", ""))
        gem_text = clean_text(row.get("gemsetting", ""))
        watch_type_text = clean_text(row.get("watch", ""))
        watch_movement = clean_text(row.get("watch_movement", ""))
        raw_collection = clean_text(row.get("collection", ""))
        url = clean_text(row.get("url",""))


        # Case Size(mm) — diameter
        diameter_val = parse_case_diameter(case_text)

        # Collection Title
        collection_titlecase = raw_collection.replace("-", " ").title()

        # Title
        title_val = f"Patek Philippe {collection_titlecase} Watch"

        # Product Subtitle
        product_subtitle_val = build_product_subtitle(sku_raw, collection_titlecase)

        # Description
        description_val = desc

        # Material (Case)
        material_val = parse_case_material(case_text)

        # Movement Type
        movement_type_val = parse_movement_type(watch_type_text, watch_movement)

        # Short Description = [Material, <diameter> mm, Movement]
        short_parts = []
        if material_val:
            short_parts.append(material_val)
        if diameter_val:
            short_parts.append(diameter_val + " mm")
        if movement_type_val:
            short_parts.append(movement_type_val)
        short_desc_val = ", ".join(short_parts)

        # Collection
        collection_val = collection_titlecase
        
        # Collection Description
        collection_desc_val = ""  # если нет

        # Model
        model_val = collection_titlecase

        # Ref Number
        ref_number_val = sku_raw

        # Brands
        brands_val = "Patek Philippe"

        # Type
        type_val = "Watches"

        # Case Material = Material
        case_material_val = material_val

        # Strap Type
        strap_type_val = parse_strap_type(strap_text)

        # Strap Color
        strap_color_val = parse_strap_color(strap_text)

        # Dial Color
        dial_color_val = parse_dial_color(dial_text)

        # Case Dimensions
        size_dimensions_val = build_size_dimensions(case_text, diameter_val)

        #Case Height
        height_val = parse_case_height(case_text)

        # Water Resistance
        water_res_val = parse_water_resistance(case_text)

        # Gender
        gender_val, gender_new_val = determine_gender_by_size(diameter_val)

        # Buckle
        buckle_val = parse_buckle(strap_text)

        # Crystal
        crystal_val = parse_crystal(case_text)

        # Watch Shape
        shape_val = parse_watch_shape(raw_collection)

        # Gemstones
        gem_val, gem_desc_val = parse_gemsetting_info(gem_text)

        # Call for Price = Yes
        call_for_price_val = "Yes"

        # URL
        url_val = url

        row_out = {
            "Title": title_val,
            "Product Subtitle": product_subtitle_val,
            "Description": description_val,
            "Short Description": short_desc_val,
            "Collection": collection_val,
            "Collection Description": collection_desc_val,
            "Model": model_val,
            "Ref Number": ref_number_val,
            "Brands": brands_val,
            "Type": type_val,
            "Material": material_val,
            "Case Material": case_material_val,
            "Strap Type": strap_type_val,
            "Strap Color": strap_color_val,
            "Dial Color": dial_color_val,
            "Case Size(mm)": diameter_val,
            "Size/Dimensions": size_dimensions_val,
            "Case Height": height_val,
            "Water Resistance": water_res_val,
            "Gender": gender_val,
            "Gender New": gender_new_val,
            "Buckle": buckle_val,
            "Crystal": crystal_val,
            "Movement Type": movement_type_val,
            "Watch Shape": shape_val,
            "Gemstones": gem_val,
            "Gemstones Description": gem_desc_val,
            "Call for Price": call_for_price_val,
            "URL": url_val
        }

        results.append(row_out)

    # Build it into a DataFrame
    df_out = pd.DataFrame(results, columns=out_cols)

    # Save the result to CSV and XLSX with a name based on output_base
    df_out.to_csv(f"{output_base}.csv", index=False, encoding="utf-8-sig")
    df_out.to_excel(f"{output_base}.xlsx", index=False)
    print("Done: CSV and XLSX are generated. Output files:", output_base)

if __name__ == "__main__":
    main()