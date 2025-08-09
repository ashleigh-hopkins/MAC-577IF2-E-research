#!/usr/bin/env python3

import re
from collections import defaultdict
from datetime import datetime

def extract_hex_values(log_content):
    """Extract hex values from the log content with timestamps"""
    
    # Pattern to match the CODE section with timestamp
    pattern = r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?<CODE>(.*?)</CODE>'
    matches = re.findall(pattern, log_content, re.DOTALL)
    
    samples = []
    
    for timestamp_str, code_section in matches:
        # Parse timestamp
        timestamp = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M:%S')
        
        # Extract individual VALUE entries
        value_pattern = r'<VALUE>([^<]+)</VALUE>'
        values = re.findall(value_pattern, code_section)
        
        if values:
            samples.append({
                'timestamp': timestamp,
                'values': values
            })
    
    return samples

def analyze_byte_changes(samples):
    """Analyze which bytes are changing across samples"""
    
    if not samples:
        return
    
    print(f"Found {len(samples)} samples to analyze")
    print("=" * 80)
    
    # Group by VALUE position (02, 03, 04, 05, 06, 09)
    value_groups = defaultdict(list)
    
    for sample in samples:
        for i, value in enumerate(sample['values']):
            # Extract the group code (02, 03, etc)
            if len(value) >= 12:
                group_code = value[10:12]  # Positions 10-11 contain the group code
                value_groups[group_code].append({
                    'timestamp': sample['timestamp'],
                    'full_value': value,
                    'bytes': [value[j:j+2] for j in range(0, len(value), 2)]
                })
    
    # Analyze each group
    for group_code in sorted(value_groups.keys()):
        print(f"\n📊 GROUP {group_code} ANALYSIS")
        print("-" * 50)
        
        group_samples = value_groups[group_code]
        if len(group_samples) < 2:
            print("Not enough samples for comparison")
            continue
            
        # Find changing byte positions
        changing_positions = set()
        first_sample = group_samples[0]['bytes']
        
        for sample in group_samples[1:]:
            for pos, (byte1, byte2) in enumerate(zip(first_sample, sample['bytes'])):
                if byte1 != byte2:
                    changing_positions.add(pos)
        
        print(f"Changing byte positions: {sorted(changing_positions)}")
        
# Identify potential humidity encoding pattern
        print("\n🔍 CHECKING FOR HUMIDITY PATTERN")
        previous = None
        significant_drop = None
        potential_humidity = []

        for sample in group_samples:
            curr_values = [int(b, 16) for b in sample['bytes'] if len(b) == 2]
            for value in curr_values:
                if previous is not None:
                    # Check if pattern matches: (stable or slight increase) -> decrease -> increase -> significant drop
                    if (previous <= value <= previous + 2) and significant_drop is None:
                        if len(potential_humidity) == 0 or potential_humidity[-1] == 'drop':
                            potential_humidity.append('same_or_increase')
                        elif potential_humidity[-1] == 'same_or_increase':
                            continue
                    elif value < previous and potential_humidity[-1] == 'same_or_increase':
                        potential_humidity.append('drop')
                    elif value > previous and potential_humidity[-1] == 'drop':
                        significant_drop = value
                        break
                previous = value
            if significant_drop:
                print(f"Humidity pattern detected at {sample['timestamp']} in group {group_code}: {curr_values}")
                break
            else:
                # Reset if pattern breaks
                potential_humidity = []
        print(f"\nTIME        ", end="")
        for pos in range(min(len(first_sample), 20)):  # Show first 20 bytes
            if pos in changing_positions:
                print(f" {pos:2d}*", end="")
            else:
                print(f" {pos:2d} ", end="")
        print()
        
        for sample in group_samples:
            time_str = sample['timestamp'].strftime('%H:%M:%S')
            print(f"{time_str}   ", end="")
            
            for pos in range(min(len(sample['bytes']), 20)):
                byte_val = sample['bytes'][pos]
                if pos in changing_positions:
                    print(f" {byte_val}*", end="")
                else:
                    print(f" {byte_val} ", end="")
            print()
        
        # Show decimal values for changing bytes
        if changing_positions:
            print(f"\nChanging bytes in decimal:")
            print(f"TIME        ", end="")
            for pos in sorted(changing_positions):
                print(f"  Pos{pos:2d}", end="")
            print()
            
            for sample in group_samples:
                time_str = sample['timestamp'].strftime('%H:%M:%S')
                print(f"{time_str}   ", end="")
                
                for pos in sorted(changing_positions):
                    if pos < len(sample['bytes']):
                        decimal_val = int(sample['bytes'][pos], 16)
                        print(f"   {decimal_val:3d}", end="")
                print()
        
        print()

def main():
    # Read the log file
    log_file = "/Users/ashhopkins/Desktop/untitled text.txt"
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Extract and analyze the data
    samples = extract_hex_values(content)
    analyze_byte_changes(samples)
    
    # Look for potential humidity values (typically 50-70% range)
    print("\n🔍 LOOKING FOR POTENTIAL HUMIDITY VALUES")
    print("=" * 50)
    print("Searching for bytes with values in 50-70 range (typical humidity)...")
    
    if samples:
        for group_code in ['02', '03', '04', '05', '06', '09']:
            for sample in samples:
                if len(sample['values']) > 0:
                    for i, value in enumerate(sample['values']):
                        if len(value) >= 12 and value[10:12] == group_code:
                            bytes_list = [value[j:j+2] for j in range(0, len(value), 2)]
                            time_str = sample['timestamp'].strftime('%H:%M:%S')
                            
                            humidity_candidates = []
                            for pos, byte_hex in enumerate(bytes_list):
                                try:
                                    decimal_val = int(byte_hex, 16)
                                    if 50 <= decimal_val <= 70:
                                        humidity_candidates.append((pos, byte_hex, decimal_val))
                                except ValueError:
                                    continue
                            
                            if humidity_candidates:
                                print(f"Group {group_code} @ {time_str}: {humidity_candidates}")
                            break

if __name__ == "__main__":
    main()
