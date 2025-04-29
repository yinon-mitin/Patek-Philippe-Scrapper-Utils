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
    """
    Extracts the case diameter value from text like 'Diameter: 38 mm'
    and returns it formatted as '<float>.1f mm'.
    """
    pattern = (
        r"(?:[Cc]ase\s+)?[Dd]iameter"
        r"(?:\s*\([^)]*\))?"
        r"\s*[:\-]?\s*"
        r"(\d+(?:[.,]\d+)?)"
        r"(?:[\s\u00A0\u2009]*mm\.?)"
    )
    match = re.search(pattern, case_text)
    if match:
        val = float(match.group(1).replace(",", "."))
        return f"{val:.1f} mm"
    return ""

def parse_case_dimensions(case_text: str) -> str:
    """
    Extracts the case dimensions value from text, e.g., "Dimensions: 28.6 x 40.85 mm".
    """
    pattern = (
        r"(?:[Cc]ase\s+)?[Dd]imension(?:s)?\s*:\s*"
        r"([\d\.,\s×x\-–Éé]+mm)"
    )
    match = re.search(pattern, case_text)
    return match.group(1).strip() if match else ""

def parse_case_thickness(case_text: str) -> str:
    """
    Extracts thickness from case text using various possible labels:
    'Thickness: 7.3 mm', 'Height: 8,08 mm', etc.

    Returns:
        str: Normalized thickness value with 'mm' or empty string if not found.
    """
    pattern = (
        r"(?:[Tt]hickness|[Hh]eight)"     # Keywords
        r"\s*[:\-]?\s*"                   # Optional formatting characters
        r"(\d+(?:[.,]\d+)?)"              # Number with dot or comma
        r"\s*mm\b"
    )
    match = re.search(pattern, case_text)
    if match:
        # Normalize to use dot (.)
        value = match.group(1).replace(",", ".").strip()
        return f"{value} mm"
    return ""

def extract_largest_from_dimensions(dimensions: str) -> str:
    """
    Extracts the largest number from a case dimensions string like '25.5 x 35 mm'
    and returns it with 'mm'. Used as fallback for case_size.
    """
    if not dimensions:
        return ""
    
    # Match numbers in formats like 25.5, 35, 25,5 etc.
    number_pattern = r"(\d+(?:[.,]\d+)?)"
    numbers = re.findall(number_pattern, dimensions)
    if not numbers:
        return ""
    
    # Normalize numbers to float for comparison
    float_numbers = [float(n.replace(",", ".")) for n in numbers]
    largest = max(float_numbers)
    return f"{largest:.1f} mm"

# def build_size_dimensions(case_text: str, diameter_val: str) -> str:
    
    # Returns the value for the “Size/Dimensions” column in the format:
    # - “xx.x mm x yy.y mm” if both diameter and thickness are found
    # - “xx.x mm” if only diameter is found
    # - If there is no diameter data in the case, returns an empty string.
    # 
    # If dimensions are explicitly present in the text (e.g., “Case dimensions: ...”),
    # the function uses them in their entirety. Otherwise, it assembles the string from diameter and thickness/thickness.
    
    # If explicit dimensions are present, we use them:
    dims = parse_case_dimensions(case_text)
    if dims:
        return dims.strip()

    # Try to extract thickness/thickness:
    thickness_val = parse_case_thickness(case_text)
    
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
        if thickness_val:
            thickness_num = float(thickness_val)
            thickness_formatted = f"{thickness_num:.1f}"
        else:
            thickness_formatted = ""
    except ValueError:
        thickness_formatted = thickness_val

    if diameter_formatted and thickness_formatted:
        return f"{diameter_formatted} mm x {thickness_formatted} mm"
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


# === Other (Gender, Movement, Gemstones...) ===

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
        "twenty~4": "Round",
        "pocket watches": "Round",
        "gondolo": "Rectangular",
        "golden ellipse": "Elipse",
        "nautilus": "Octagon",
        "aquanaut": "Octagon",
        "cubitus": "Square"
    }
    return shape_map.get(name, "")

def parse_movement_type(movement_type: str) -> str:
    """
    Parses the movement type from the new 'movement_type' field.
    Recognizes 'automatic', 'manual', 'quartz', or returns empty string if not matched.
    
    Args:
        movement_type (str): Raw movement type text.

    Returns:
        str: Normalized movement type ("Automatic", "Manual", "Quartz", or "").
    """
    mt = movement_type.lower() if isinstance(movement_type, str) else ""

    if "automatic" in mt or "self-winding" in mt:
        return "Automatic"
    if "manual" in mt or "hand-wound" in mt:
        return "Manual"
    if "quartz" in mt:
        return "Quartz"

    return ""

# def determine_gender_by_size(diameter_str: str) -> (str, str):
    
    # Determines values for Gender and Gender New based on Case Size (diameter).
    # 
    # Argument:
    # diameter_str: extracted diameter (e.g., “40.5”)
    # 
    # Returns:
    # (gender, gender_new)
    # - If diameter is less than 36 mm: (“For Her”, “For Her”)
    # - If the diameter is 38 mm or more: (“For Him, For Her”, “For Him, For Her")
    # - If the diameter is between 36 and 38 mm: (“For Him, For Her”, “For Him, For Her”) (the threshold can be changed)
    
    try:
        d = float(diameter_str)
    except (ValueError, TypeError):
        # If it fails to convert, default to male
        return ("For Him, For Her", "For Him")
    
    if d < 36:
        return ("For Her", "For Her")
    elif d >= 38:
        return ("For Him, For Her", "For Him, For Her")
    else:
        # For intermediate values (36-38 mm) default to male orientation
        return ("For Him, For Her", "For Him, For Her")

def map_gender_fields(gender: str) -> tuple[str, str]:
    """
    Maps 'Men' or 'Ladies' to two fields:
    - original gender to gender_new
    - human-readable label to gender ("For Him" / "For Her")
    """
    gender = gender.strip().lower() if isinstance(gender, str) else ""
    if gender == "men":
        return "Men", "For Him"
    elif gender == "ladies":
        return "Ladies", "For Her"
    else:
        return "", ""

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

def build_tags(brands_val: str, gender_val: str, ref_number_val: str) -> str:
    
    # Forms a tag string for Shopify: combines fixed and variable values.
    
    tags = ["Watches", "Luxury Brands"]

    if brands_val:
        tags.append(brands_val)
    if gender_val:
        tags.append(gender_val)
    if ref_number_val:
        tags.append(ref_number_val)

    return ", ".join(tags)

def build_handle(title: str, ref_number_val: str) -> str:

    # Creates a unique handle from title + ref_number.
    # Convert to lower case, remove special characters, replace spaces and characters with “-”.

    if not title:
        title = ""
    if not ref_number_val:
        ref_number_val = ""

    combined = f"{title}-{ref_number_val}".lower()

    # Replace anything that's not letters/numbers with “-”
    handle = re.sub(r"[^a-z0-9]+", "-", combined)

    # Take out hyphens and hyphens
    handle = handle.strip("-")

    return handle

def build_short_description(material_val: str, case_size_val: str, movement_type_val: str) -> str:
    """
    Builds a short description combining material, case size (mm), and movement type.
    
    Args:
        material_val (str): Material of the watch case (e.g., "Rose Gold").
        case_size_val (str): Diameter of the watch case (without 'mm').
        movement_type_val (str): Movement type (e.g., "Self-winding").

    Returns:
        str: A short description like "Rose Gold, 38.8 mm, Self-winding".
    """
    short_parts = []
    if material_val:
        short_parts.append(material_val)
    if case_size_val:
        short_parts.append(case_size_val)
    if movement_type_val:
        short_parts.append(movement_type_val)
    return ", ".join(short_parts)

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
    print("The file has been successfully read:", args.input)

    # List of output columns
    out_cols = [
        "Handle",
        "Title",
        "Metafield: custom.product_subtitle [single_line_text_field]",
        "Body HTML",
        "Metafield: description_tag [multi_line_text_field]",
        "Metafield: short_description [multi_line_text_field]",
        "Metafield: cartier_collection [single_line_text_field]",
        #"Collection Description",
        "Metafield: model [single_line_text_field]",
        "Metafield: ref_number [single_line_text_field]",
        "Metafield: brands [single_line_text_field]",
        "Vendor",
        "Category: Name",
        "Tags",
        "Metafield: type [single_line_text_field]",
        "Metafield: material [single_line_text_field]",
        "Metafield: case_material [single_line_text_field]",
        "Metafield: type_of_strap [single_line_text_field]",
        "Metafield: strap_color [single_line_text_field]",
        "Metafield: dial_color [single_line_text_field]",
        "Metafield: case_size [single_line_text_field]",
        "Metafield: watch_dimensions [single_line_text_field]",
        "Metafield: custom.thickness [single_line_text_field]",
        "Metafield: water_resistance [single_line_text_field]",
        "Metafield: gender [single_line_text_field]",
        "Metafield: gender_new [single_line_text_field]",
        "Metafield: buckle [single_line_text_field]",
        "Metafield: crystal [single_line_text_field]",
        "Metafield: movement [single_line_text_field]",
        "Metafield: movement_type [single_line_text_field]",
        "Metafield: watch_shape [single_line_text_field]",
        "Metafield: custom.gemstones [single_line_text_field]",
        "Metafield: custom.gemstones_description [single_line_text_field]",
        "Metafield: callforprice [single_line_text_field]",
        #"URL"
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
        caliber_val = clean_text(row.get("caliber", ""))
        raw_collection = clean_text(row.get("collection", ""))
        gender_raw = clean_text(row.get("gender", ""))
        url = clean_text(row.get("url",""))


        # Case Size(mm) — diameter
        case_size_val = parse_case_diameter(case_text)

        # Case Dimensions
        watch_dimensions_val = parse_case_dimensions(case_text)

        # Fallback: if case_size is empty, use the largest dimension
        if not case_size_val and watch_dimensions_val:
            case_size_val = extract_largest_from_dimensions(watch_dimensions_val)

        #Case thickness
        thickness_val = parse_case_thickness(case_text)

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
        movement_type_val = parse_movement_type(row.get("movement_type", ""))

        # Short Description
        short_desc_val = build_short_description(material_val, case_size_val, movement_type_val)

        # Collection
        collection_val = collection_titlecase
        
        # Collection Description
        collection_desc_val = ""  # если нет

        # Model
        model_val = remove_sku_suffix(sku_raw)

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

        # Water Resistance
        water_res_val = parse_water_resistance(case_text)

        # Gender
        # gender_val, gender_new_val = determine_gender_by_size(diameter_val)
        gender_new_val, gender_val = map_gender_fields(gender_raw)

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

        # Tags
        tags_val = build_tags(brands_val, gender_val, ref_number_val)

        # Handle
        handle_val = build_handle(title_val, ref_number_val)

        # URL
        url_val = url

        row_out = {
            "Handle": handle_val,
            "Title": title_val,
            "Metafield: custom.product_subtitle [single_line_text_field]": product_subtitle_val,
            "Body HTML": description_val,
            "Metafield: description_tag [multi_line_text_field]": description_val,
            "Metafield: short_description [multi_line_text_field]": short_desc_val,
            "Metafield: cartier_collection [single_line_text_field]": collection_val,
            ## Don't needed "Collection Description": collection_desc_val,
            "Metafield: model [single_line_text_field]": model_val,
            "Metafield: ref_number [single_line_text_field]": ref_number_val,
            "Metafield: brands [single_line_text_field]": brands_val,
            "Vendor": brands_val,
            "Category: Name": type_val,
            "Tags": tags_val,
            "Metafield: type [single_line_text_field]": type_val,
            "Metafield: material [single_line_text_field]": material_val,
            "Metafield: case_material [single_line_text_field]": case_material_val,
            "Metafield: type_of_strap [single_line_text_field]": strap_type_val,
            "Metafield: strap_color [single_line_text_field]": strap_color_val,
            "Metafield: dial_color [single_line_text_field]": dial_color_val,
            "Metafield: case_size [single_line_text_field]": case_size_val,
            "Metafield: watch_dimensions [single_line_text_field]": watch_dimensions_val,
            "Metafield: custom.thickness [single_line_text_field]": thickness_val,
            "Metafield: water_resistance [single_line_text_field]": water_res_val,
            "Metafield: gender [single_line_text_field]": gender_val,
            "Metafield: gender_new [single_line_text_field]": gender_new_val,
            "Metafield: buckle [single_line_text_field]": buckle_val,
            "Metafield: crystal [single_line_text_field]": crystal_val,
            "Metafield: movement [single_line_text_field]": caliber_val,
            "Metafield: movement_type [single_line_text_field]": movement_type_val,
            "Metafield: watch_shape [single_line_text_field]": shape_val,
            "Metafield: custom.gemstones [single_line_text_field]": gem_val,
            "Metafield: custom.gemstones_description [single_line_text_field]": gem_desc_val,
            "Metafield: callforprice [single_line_text_field]": call_for_price_val,
            # Don't needed "URL": url_val
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