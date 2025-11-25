#!/usr/bin/env python3
"""
BTCMap to OpenStreetMap Tag Converter
Converts BTCMap data format to OSM tag format for easy copy-paste
"""

import re
import json
from datetime import datetime
from typing import Dict, List


def parse_address(address_str: str) -> Dict[str, str]:
    """
    Parse address string into components.
    Handles various formats including suite numbers and road types like FM roads.
    Format examples:
    - "449 Standridge Trl Cleveland AL 35049-4554 US"
    - "26750 FM 1093 STE 120 Richmond TX 77406 US"
    """
    parts = {}
    
    if not address_str:
        return parts
    
    # Valid US state abbreviations (exclude common road prefixes)
    valid_states = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
    }
    
    # Remove country code if present
    address = address_str.replace(" US", "").strip()
    
    # Try to extract state first (2-letter abbreviation, must be valid US state)
    # Look for state - zip code typically comes after state
    state_match = None
    state_pos = -1
    for state in valid_states:
        # Match state as whole word, typically before zip or at end
        pattern = r'\b' + re.escape(state) + r'\b'
        match = re.search(pattern, address)
        if match:
            # Make sure it's not part of a road designation (like FM, US, SR, etc.)
            pos = match.start()
            if pos > 0:
                prev_char = address[pos - 1]
                # If preceded by a letter, it might be part of a road name
                if prev_char.isalpha() and prev_char != ' ':
                    continue
            state_match = match
            state_pos = match.end()
            break
    
    # Extract postal code (5 digits, optionally with -4 digits)
    # If we found a state, zip code is typically right after it
    if state_match:
        parts['state'] = state_match.group(0)
        # Look for zip code after the state
        address_after_state = address[state_pos:].strip()
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address_after_state)
        if zip_match:
            parts['postcode'] = zip_match.group(1)
        # Remove state and zip code from address
        address = address[:state_match.start()].strip()
    else:
        # No state found, try to find zip code at the end
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', address)
        if zip_match:
            # Check if this looks like it's at the end (likely zip code)
            zip_pos = zip_match.end()
            remaining = address[zip_pos:].strip()
            if not remaining or len(remaining) < 3:  # Likely the zip code
                parts['postcode'] = zip_match.group(1)
                address = address[:zip_match.start()].strip()
    
    # Split remaining address
    address_parts = address.split()
    if not address_parts:
        return parts
    
    # Find suite/unit indicators (STE, SUITE, UNIT, #, etc.)
    suite_keywords = ['STE', 'SUITE', 'UNIT', '#', 'APT', 'APARTMENT', 'BLDG', 'BUILDING']
    suite_indices = set()  # Track all indices that are part of suite (indicator + value)
    suite_value = None
    
    for i, part in enumerate(address_parts):
        part_upper = part.upper()
        if part_upper in suite_keywords:
            if i + 1 < len(address_parts):
                suite_indices.add(i)  # Suite indicator
                suite_indices.add(i + 1)  # Suite value
                suite_value = address_parts[i + 1]
                break
        elif part.startswith('#') and len(part) > 1:
            suite_indices.add(i)  # The "#3" token itself
            suite_value = part[1:]  # Remove the #
            break
    
    # Extract house number (usually first number in address)
    housenumber = None
    housenumber_index = -1
    for i, part in enumerate(address_parts):
        if part.isdigit() and i == 0:  # First part being a number is likely house number
            housenumber = part
            housenumber_index = i
            break
    
    # Determine city (usually the last capitalized word before state)
    # City is typically a proper noun, so look for capitalized words
    # But exclude street suffixes, road types, and directional prefixes
    city = None
    city_index = -1
    
    # Common street suffixes and road types to exclude
    street_suffixes = {
        'ST', 'STREET', 'AVE', 'AVENUE', 'RD', 'ROAD', 'BLVD', 'BOULEVARD',
        'DR', 'DRIVE', 'LN', 'LANE', 'CT', 'COURT', 'PL', 'PLACE', 'WAY',
        'CIR', 'CIRCLE', 'PKWY', 'PARKWAY', 'TRL', 'TRAIL', 'TER', 'TERRACE',
        'FM', 'US', 'SR', 'CR', 'HWY', 'HIGHWAY', 'ROUTE', 'RT'
    }
    
    # Directional prefixes to exclude (N, S, E, W, North, South, etc.)
    directionals = {'N', 'S', 'E', 'W', 'N.', 'S.', 'E.', 'W.', 
                    'NORTH', 'SOUTH', 'EAST', 'WEST', 'NE', 'NW', 'SE', 'SW',
                    'N.E.', 'N.W.', 'S.E.', 'S.W.'}
    
    # Work backwards to find city (skip street suffixes and directionals)
    # City can be multiple words (e.g., "Los Angeles", "New York")
    # Collect capitalized words at the end that aren't suffixes or suite parts
    city_parts = []
    city_start_index = -1
    
    for i in range(len(address_parts) - 1, -1, -1):
        part = address_parts[i]
        # Skip if it's a suite indicator or number
        if i in suite_indices:
            # If we hit a suite, we've passed the city
            break
        if i == housenumber_index:
            # If we hit the house number, we've passed the city
            break
        # If it's a capitalized word (starts with capital), check if it's part of city
        if part and part[0].isupper() and not part.isdigit():
            part_upper = part.upper().rstrip('.')  # Remove trailing period
            # If it's a street suffix or directional, we've reached the end of city
            if part_upper in street_suffixes or part_upper in directionals:
                break
            # This could be part of the city name
            city_parts.insert(0, part)  # Insert at beginning to maintain order
            city_start_index = i
        else:
            # If we hit a non-capitalized word (that's not a suite), we've passed the city
            if i not in suite_indices and part and not part[0].isdigit():
                break
    
    if city_parts:
        city = ' '.join(city_parts)
        city_index = city_start_index
    
    if city:
        parts['city'] = city
    
    # Extract street (everything between house number and city, excluding suite)
    street_parts = []
    start_idx = housenumber_index + 1 if housenumber_index >= 0 else 0
    end_idx = city_index if city_index >= 0 else len(address_parts)
    
    for i in range(start_idx, end_idx):
        # Skip suite indicator and suite number
        if i in suite_indices:
            continue
        street_parts.append(address_parts[i])
    
    if street_parts:
        parts['street'] = ' '.join(street_parts)
    
    if housenumber:
        parts['housenumber'] = housenumber
    
    if suite_value:
        parts['unit'] = suite_value
    
    return parts


def map_category_to_osm(category: str) -> list:
    """
    Map BTCMap category to OSM shop/amenity tags.
    Returns a list of tag strings (can be multiple tags for special cases).
    """
    category_mapping = {
        'professional_services': 'office',
        'restaurants': 'restaurant',
        'cafe': 'cafe',
        'retail': 'shop',
        'confectionery': 'shop',
        'food': 'shop',
        'grocery': 'supermarket',
        'bar': 'bar',
        'hotel': 'hotel',
        'gas_station': 'fuel',
        'food_truck_cart': 'fast_food',
    }
    
    # Special cases that need additional tags
    special_cases = {
        'food_truck_cart': ['street_vendor=yes'],
    }
    
    tags = []
    
    # If category contains shop-related terms, use shop tag
    if 'shop' in category or category in ['retail', 'confectionery', 'food']:
        tags.append(f'shop={category}')
    elif category in category_mapping:
        mapped = category_mapping[category]
        if mapped in ['shop', 'supermarket', 'fuel']:
            tags.append(f'shop={mapped}')
        else:
            tags.append(f'amenity={mapped}')
    else:
        # Default to shop if unknown
        tags.append(f'shop={category}')
    
    # Add additional tags for special cases
    if category in special_cases:
        tags.extend(special_cases[category])
    
    return tags


def infer_cuisine_from_name(name: str) -> List[str]:
    """
    Infer cuisine tags from business name.
    Returns a list of cuisine tags (can be multiple).
    """
    if not name:
        return []
    
    name_lower = name.lower()
    cuisine_tags = []
    
    # Mapping of keywords to cuisine values
    cuisine_keywords = {
        'coffee': 'coffee',
        'cafe': 'coffee',
        'café': 'coffee',
        'espresso': 'coffee',
        'latte': 'coffee',
        'burger': 'burger',
        'burgers': 'burger',
        'bubble tea': 'bubble_tea',
        'boba': 'bubble_tea',
        'pizza': 'pizza',
        'pizzeria': 'pizza',
        'sushi': 'sushi',
        'taco': 'mexican',
        'tacos': 'mexican',
        'burrito': 'mexican',
        'mexican': 'mexican',
        'thai': 'thai',
        'chinese': 'chinese',
        'japanese': 'japanese',
        'indian': 'indian',
        'italian': 'italian',
        'bbq': 'bbq',
        'barbecue': 'Barbecue',
        'barbeque': 'Barbecue',
        'seafood': 'seafood',
        'steak': 'Steak_house',
        'steakhouse': 'Steak_house',
        'ice cream': 'ice_cream',
        'gelato': 'ice_cream',
        'bakery': 'bakery',
        'deli': 'deli',
        'sandwich': 'Sandwich',
        'sub': 'Sandwich',
        'subs': 'Sandwich',
    }
    
    # Check for matches (longer phrases first to avoid partial matches)
    # Sort by length descending to match longer phrases first
    sorted_keywords = sorted(cuisine_keywords.items(), key=lambda x: len(x[0]), reverse=True)
    
    for keyword, cuisine in sorted_keywords:
        if keyword in name_lower:
            cuisine_tags.append(f'cuisine={cuisine}')
            # Don't break - allow multiple cuisine tags if name contains multiple keywords
    
    return cuisine_tags


def convert_btcmap_to_osm(data: Dict) -> str:
    """
    Convert BTCMap data to OSM tag format.
    """
    today = datetime.now().strftime('%Y-%m-%d')
    
    output_lines = []
    
    # Parse address
    if 'address' in data.get('extra_fields', {}):
        address_parts = parse_address(data['extra_fields']['address'])
        
        if 'city' in address_parts:
            output_lines.append(f"addr:city={address_parts['city']}")
        if 'housenumber' in address_parts:
            output_lines.append(f"addr:housenumber={address_parts['housenumber']}")
        if 'postcode' in address_parts:
            output_lines.append(f"addr:postcode={address_parts['postcode']}")
        if 'state' in address_parts:
            output_lines.append(f"addr:state={address_parts['state']}")
        if 'street' in address_parts:
            output_lines.append(f"addr:street={address_parts['street']}")
        if 'unit' in address_parts:
            output_lines.append(f"addr:unit={address_parts['unit']}")
    
    # Add check dates
    output_lines.append(f"check_date:currency:XBT={today}")
    output_lines.append(f"check_date={today}")
    
    # Add currency and payment fields
    output_lines.append("currency:XBT=yes")
    output_lines.append("payment:onchain=no")
    output_lines.append("payment:lightning=yes")
    output_lines.append("payment:lightning_contactless=no")
    
    # Add lightning operator from Origin
    origin = data.get('origin', '').lower()
    if origin:
        output_lines.append(f"payment:lightning:operator={origin}")
    
    # Add name
    if 'name' in data:
        output_lines.append(f"name={data['name']}")
        
        # Infer cuisine from name
        cuisine_tags = infer_cuisine_from_name(data['name'])
        output_lines.extend(cuisine_tags)
    
    # Add opening hours if available
    if 'opening_hours' in data.get('extra_fields', {}):
        output_lines.append(f"opening_hours={data['extra_fields']['opening_hours']}")
    
    # Add category/shop (can be multiple tags for special cases)
    if 'category' in data:
        osm_tags = map_category_to_osm(data['category'])
        output_lines.extend(osm_tags)
    
    # Add phone if available (not in example but might be in some data)
    if 'phone' in data.get('extra_fields', {}):
        output_lines.append(f"phone={data['extra_fields']['phone']}")
    
    # Add website if available
    if 'website' in data.get('extra_fields', {}):
        output_lines.append(f"website={data['extra_fields']['website']}")
    
    # Add wheelchair if available
    if 'wheelchair' in data.get('extra_fields', {}):
        output_lines.append(f"wheelchair={data['extra_fields']['wheelchair']}")
    
    return '\n'.join(output_lines)


def parse_btcmap_input(text: str) -> Dict:
    """
    Parse the BTCMap input format from text.
    """
    data = {}
    extra_fields = {}
    
    lines = text.strip().split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if line.startswith('Id:'):
            data['id'] = line.split(':', 1)[1].strip()
        elif line.startswith('Origin:'):
            data['origin'] = line.split(':', 1)[1].strip()
        elif line.startswith('Name:'):
            data['name'] = line.split(':', 1)[1].strip()
        elif line.startswith('Category:'):
            data['category'] = line.split(':', 1)[1].strip()
        elif line.startswith('Extra fields:'):
            current_section = 'extra_fields'
        elif line.startswith('{'):
            # Start of JSON
            json_str = line
            # Collect all lines until closing brace
            brace_count = line.count('{') - line.count('}')
            idx = lines.index(line) + 1
            while brace_count > 0 and idx < len(lines):
                json_str += '\n' + lines[idx]
                brace_count += lines[idx].count('{') - lines[idx].count('}')
                idx += 1
            
            try:
                extra_fields = json.loads(json_str)
                data['extra_fields'] = extra_fields
            except json.JSONDecodeError:
                # Try to parse manually if JSON fails
                pass
    
    return data


def main():
    """
    Main interactive function.
    """
    import sys
    
    # Check if file path provided as argument
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                input_text = f.read()
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            return
        except Exception as e:
            print(f"Error reading file: {e}")
            return
    else:
        print("=" * 60)
        print("BTCMap to OpenStreetMap Tag Converter")
        print("=" * 60)
        print("\nPaste your BTCMap data below (press Ctrl+D or Ctrl+Z when done):\n")
        
        # Read input
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        
        input_text = '\n'.join(lines)
    
    if not input_text.strip():
        print("\nNo input provided. Exiting.")
        return
    
    try:
        # Parse input
        btcmap_data = parse_btcmap_input(input_text)
        
        # Convert to OSM format
        osm_output = convert_btcmap_to_osm(btcmap_data)
        
        # Display output
        if len(sys.argv) <= 1:
            print("\n" + "=" * 60)
        print("OpenStreetMap Tag Format:")
        print("=" * 60)
        print(osm_output)
        print("=" * 60)
        if len(sys.argv) <= 1:
            print("\n(Output copied above - ready to paste into OSM)")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

