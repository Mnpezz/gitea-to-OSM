# BTCMap to OpenStreetMap Tag Converter

A Python tool to quickly convert BTCMap data into OpenStreetMap tag format for easy tagging.

## Features

- Parses BTCMap data format (Id, Origin, Name, Category, Extra fields)
- Automatically extracts and formats address components (city, housenumber, postcode, state, street)
- Adds required Bitcoin/Lightning payment tags with today's date
- Maps BTCMap categories to OSM shop/amenity tags
- Preserves opening hours and other metadata

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## Usage

### Interactive Mode (Recommended)

Run the program and paste your BTCMap data:

```bash
python3 btcmap_to_osm.py
```

**Important Terminal Tips:**
- **To paste**: Use `Ctrl+Shift+V` (or right-click and select paste)
- **To copy output**: Select the text and use `Ctrl+Shift+C` (or right-click and select copy)
- **To finish input**: Press `Ctrl+D` (Linux/Mac) or `Ctrl+Z` then Enter (Windows)

The program will wait for you to paste your data, then display the OSM format output.

### File Mode

If you have your BTCMap data saved in a file:

```bash
python3 btcmap_to_osm.py input_file.txt
```

## Input Format

Paste your BTCMap data in this format:

```
Id: 3901
Origin: square
Name: Dulcédo Coffee
Category: food_truck_cart

Extra fields:

{
"address": "26750 FM 1093 STE 120 Richmond TX 77406 US",
"icon_url": "https://square-web-production-f.squarecdn.com/files/107fa80f57d2db9874dda1a19683578392ed87b8/original.jpeg",
"description": "Specialty coffee shop",
"opening_hours": "Mo-Sa 07:00-19:00",
"last_updated": "2025-11-25T17:21:07.561595515Z"
}
```

## Output Format

The program generates OpenStreetMap tags in this format:

```
addr:city=Richmond
addr:housenumber=26750
addr:postcode=77406
addr:state=TX
addr:street=FM 1093
addr:unit=120
check_date:currency:XBT=2025-11-25
check_date=2025-11-25
currency:XBT=yes
payment:onchain=no
payment:lightning=yes
payment:lightning_contactless=no
payment:lightning:operator=square
name=Dulcédo Coffee
cuisine=coffee
opening_hours=Mo-Sa 07:00-19:00
amenity=fast_food
street_vendor=yes
```

** unfortunally this example IS NOT a food truck even though the category shows it as such. it is a cafe. this is to show that not all inputs will give correct info but it will give you a quicker start. Be mindful. 

## Automatic Fields

The program automatically adds these fields with today's date:

- `currency:XBT=yes`
- `check_date:currency:XBT=<today's date>`
- `check_date=<today's date>`
- `payment:onchain=no`
- `payment:lightning=yes`
- `payment:lightning_contactless=no`
- `payment:lightning:operator=<from Origin field>`

## Category Mapping

BTCMap categories are automatically mapped to OSM tags:
- `professional_services` → `amenity=office`
- `restaurants` → `amenity=restaurant`
- `cafe` → `amenity=cafe`
- `confectionery` → `shop=confectionery`
- `grocery` → `shop=supermarket`
- And more...

## Tips

- The program handles various address formats, but you may need to manually verify street names (e.g., "Trl" vs "Trail")
- All dates are automatically set to today's date - no need to update manually
- The output is ready to copy directly into OpenStreetMap editors
- If you encounter parsing issues, check that your input format matches the expected structure

## Troubleshooting

- **Can't paste in terminal?** Make sure you're using `Ctrl+Shift+V` (not just `Ctrl+V`)
- **Can't copy output?** Select the text and use `Ctrl+Shift+C` or right-click
- **Address parsing looks wrong?** The program does its best, but you may need to manually adjust street names or address components
- **Category not mapping correctly?** You can edit the `map_category_to_osm()` function in the script to add more mappings
