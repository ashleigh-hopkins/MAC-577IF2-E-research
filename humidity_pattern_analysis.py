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

def analyze_humidity_patterns(samples):
    """Look for humidity patterns that match dehumidifier behavior"""
    
    print(f"🔍 ANALYZING HUMIDITY PATTERNS")
    print("=" * 60)
    
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
    
    # Look for patterns in each byte position across all groups
    for group_code in sorted(value_groups.keys()):
        group_samples = value_groups[group_code]
        if len(group_samples) < 10:  # Need enough samples to see pattern
            continue
            
        print(f"\n📊 GROUP {group_code} - HUMIDITY PATTERN ANALYSIS")
        print("-" * 50)
        
        # Check each byte position for humidity-like patterns
        max_bytes = max(len(sample['bytes']) for sample in group_samples)
        
        for byte_pos in range(max_bytes):
            byte_values = []
            timestamps = []
            
            for sample in group_samples:
                if byte_pos < len(sample['bytes']):
                    try:
                        decimal_val = int(sample['bytes'][byte_pos], 16)
                        byte_values.append(decimal_val)
                        timestamps.append(sample['timestamp'])
                    except ValueError:
                        continue
            
            if len(byte_values) < 10:
                continue
                
            # Look for humidity pattern: stable -> slight increase -> decrease -> increase -> significant drop
            pattern_found = analyze_dehumidifier_pattern(byte_values, timestamps, group_code, byte_pos)
            
            if pattern_found:
                print(f"✅ POTENTIAL HUMIDITY SENSOR at byte position {byte_pos}")
                print_pattern_timeline(byte_values, timestamps)

def analyze_dehumidifier_pattern(values, timestamps, group_code, byte_pos):
    """Analyze if values show expected dehumidifier pattern"""
    
    if len(values) < 10:
        return False
    
    # Look for the expected pattern phases
    stable_phase = []
    slight_increase_phase = []
    decrease_phase = []
    increase_phase = []
    significant_drop_phase = []
    
    # Phase detection
    for i in range(1, len(values)):
        prev_val = values[i-1]
        curr_val = values[i]
        diff = curr_val - prev_val
        
        # Detect phases based on value changes
        if abs(diff) <= 1:  # Stable (within 1 unit)
            stable_phase.append(i)
        elif 1 < diff <= 3:  # Slight increase
            slight_increase_phase.append(i)
        elif -5 <= diff < -1:  # Moderate decrease
            decrease_phase.append(i)
        elif 1 < diff <= 5:  # Moderate increase
            increase_phase.append(i)
        elif diff < -10:  # Significant drop
            significant_drop_phase.append(i)
    
    # Check if we have the expected pattern sequence
    has_stable = len(stable_phase) > 3
    has_slight_increase = len(slight_increase_phase) > 0
    has_decrease = len(decrease_phase) > 2
    has_increase = len(increase_phase) > 1
    has_significant_drop = len(significant_drop_phase) > 0
    
    # Additional check: overall range should be reasonable for humidity (20-100%)
    min_val = min(values)
    max_val = max(values)
    reasonable_range = 20 <= min_val <= 100 and 20 <= max_val <= 100
    
    pattern_score = sum([has_stable, has_slight_increase, has_decrease, has_increase, has_significant_drop])
    
    if pattern_score >= 3 and reasonable_range:
        print(f"🎯 Byte position {byte_pos} in group {group_code}: Pattern score {pattern_score}/5")
        print(f"   Range: {min_val}-{max_val}, Stable: {len(stable_phase)}, Increase: {len(slight_increase_phase)}")
        print(f"   Decrease: {len(decrease_phase)}, Re-increase: {len(increase_phase)}, Drop: {len(significant_drop_phase)}")
        return True
    
    return False

def print_pattern_timeline(values, timestamps):
    """Print the timeline of values to visualize the pattern"""
    print("\n📈 VALUE TIMELINE:")
    print("TIME      VALUE  CHANGE")
    print("-" * 25)
    
    for i, (val, ts) in enumerate(zip(values, timestamps)):
        change = ""
        if i > 0:
            diff = val - values[i-1]
            if diff > 0:
                change = f"+{diff}"
            elif diff < 0:
                change = f"{diff}"
            else:
                change = "0"
        
        print(f"{ts.strftime('%H:%M:%S')}  {val:3d}    {change}")
    
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
    print(f"Found {len(samples)} samples to analyze")
    
    analyze_humidity_patterns(samples)

if __name__ == "__main__":
    main()
