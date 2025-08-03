#!/usr/bin/env python3
import json
import sys

def analyze_log(log_file):
    """Analyze the device log to identify changing fields"""
    with open(log_file, 'r') as f:
        data = json.load(f)
    
    print(f"Analyzing {len(data)} iterations...\n")
    
    # Track changes in codes
    print("CODE Analysis:")
    print("-" * 80)
    
    # Get the number of codes
    num_codes = len(data[0]['codes'])
    
    for code_idx in range(num_codes):
        print(f"\nCODE[{code_idx}]:")
        changes = []
        
        for i in range(len(data)):
            code = data[i]['codes'][code_idx]
            iteration = data[i]['iteration']
            temp = data[i]['actual_temperature']
            fan = data[i]['actual_fan_speed']
            
            # Parse hex values
            # Skip first 12 chars (header), then parse in 2-char chunks
            header = code[:12]
            values = [code[j:j+2] for j in range(12, len(code), 2)]
            
            changes.append({
                'iteration': iteration,
                'temp': temp,
                'fan': fan,
                'header': header,
                'values': values,
                'full': code
            })
        
        # Find which bytes changed
        first_values = changes[0]['values']
        changing_positions = []
        
        for pos in range(len(first_values)):
            values_at_pos = [c['values'][pos] for c in changes]
            if len(set(values_at_pos)) > 1:
                changing_positions.append(pos)
        
        if changing_positions:
            print(f"  Changing positions: {changing_positions}")
            for pos in changing_positions:
                print(f"    Position {pos} (byte {pos + 6}):")  # +6 for header bytes
                for c in changes:
                    print(f"      Iter {c['iteration']}: {c['values'][pos]} (Temp: {c['temp']}°C, Fan: {c['fan']})")
        else:
            print("  No changes detected")
    
    # Track changes in profilecodes
    print("\n\nPROFILECODE Analysis:")
    print("-" * 80)
    
    num_profilecodes = len(data[0]['profilecodes'])
    
    for profile_idx in range(num_profilecodes):
        print(f"\nPROFILECODE[{profile_idx}]:")
        changes = []
        
        for i in range(len(data)):
            profilecode = data[i]['profilecodes'][profile_idx]
            iteration = data[i]['iteration']
            
            # Parse hex values
            header = profilecode[:12]
            values = [profilecode[j:j+2] for j in range(12, len(profilecode), 2)]
            
            changes.append({
                'iteration': iteration,
                'header': header,
                'values': values,
                'full': profilecode
            })
        
        # Find which bytes changed
        first_values = changes[0]['values']
        changing_positions = []
        
        for pos in range(len(first_values)):
            values_at_pos = [c['values'][pos] for c in changes]
            if len(set(values_at_pos)) > 1:
                changing_positions.append(pos)
        
        if changing_positions:
            print(f"  Changing positions: {changing_positions}")
            for pos in changing_positions:
                print(f"    Position {pos} (byte {pos + 6}):")
                for c in changes:
                    print(f"      Iter {c['iteration']}: {c['values'][pos]}")
        else:
            print("  No changes detected")
    
    # Energy analysis
    print("\n\nEnergy Data Analysis:")
    print("-" * 80)
    
    for i, entry in enumerate(data):
        print(f"Iteration {entry['iteration']}: Power={entry['power_watts']}W, Compressor={entry['compressor_frequency']}Hz, Operating={entry['operating']}")
    
    # Look for correlations
    print("\n\nCorrelations:")
    print("-" * 80)
    
    # Check if power consumption changed
    power_values = [entry['power_watts'] for entry in data]
    if len(set(power_values)) > 1:
        print("Power consumption changed during monitoring")
    else:
        print(f"Power consumption remained constant at {power_values[0]}W")
    
    # Check compressor frequency
    compressor_values = [entry['compressor_frequency'] for entry in data]
    if len(set(compressor_values)) > 1:
        print("Compressor frequency changed during monitoring")
    else:
        print(f"Compressor frequency remained at {compressor_values[0]}Hz")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        # Default to the most recent log
        log_file = "device_status_log_20250803_153255.json"
    
    analyze_log(log_file)
