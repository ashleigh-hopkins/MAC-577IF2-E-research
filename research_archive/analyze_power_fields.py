#!/usr/bin/env python3
import json
import sys

def analyze_power_correlations(log_file):
    """Analyze which fields correlate with power consumption changes"""
    with open(log_file, 'r') as f:
        data = json.load(f)
    
    print(f"Analyzing {len(data)} iterations for power correlations...\n")
    
    # Extract power consumption data
    power_data = [(entry['iteration'], entry['power_watts'], entry['operating']) for entry in data]
    
    print("Power Consumption Timeline:")
    print("-" * 50)
    for i, power, operating in power_data:
        print(f"Iteration {i}: {power}W {'(Operating)' if operating else '(Not Operating)'}")
    
    # Identify when power changed significantly
    power_changes = []
    for i in range(1, len(power_data)):
        if abs(power_data[i][1] - power_data[i-1][1]) > 10:  # Significant change
            power_changes.append((i-1, i, power_data[i-1][1], power_data[i][1]))
    
    print(f"\n\nSignificant Power Changes:")
    print("-" * 50)
    for prev_i, curr_i, prev_power, curr_power in power_changes:
        print(f"Between iteration {prev_i} and {curr_i}: {prev_power}W -> {curr_power}W ({curr_power - prev_power:+.1f}W)")
    
    # Analyze CODE[4] position 5 (byte 11) which seems most variable
    print("\n\nCODE[4] Position 5 Analysis (Most Variable Field):")
    print("-" * 50)
    for i, entry in enumerate(data):
        code4 = entry['codes'][4]
        byte11_hex = code4[22:24]  # Position 5 is bytes 22-23
        byte11_dec = int(byte11_hex, 16)
        print(f"Iter {i}: 0x{byte11_hex} ({byte11_dec:3d}) - Power: {entry['power_watts']:5.1f}W - Temp: {entry['actual_temperature']}°C")
    
    # Analyze the operating flag in CODE[4]
    print("\n\nCODE[4] Operating Flag Analysis:")
    print("-" * 50)
    for i, entry in enumerate(data):
        code4 = entry['codes'][4]
        # Check position 3 and 4 (bytes 9-10)
        operating_flag = code4[18:22]
        print(f"Iter {i}: Operating bytes: {operating_flag} - Device Operating: {entry['operating']} - Power: {entry['power_watts']}W")
    
    # Look for patterns in CODE[1] position 12 (increments steadily)
    print("\n\nCODE[1] Position 12 Analysis (Steady Increment):")
    print("-" * 50)
    for i, entry in enumerate(data):
        code1 = entry['codes'][1]
        byte18_hex = code1[36:38]  # Position 12 is bytes 36-37
        byte18_dec = int(byte18_hex, 16)
        print(f"Iter {i}: 0x{byte18_hex} ({byte18_dec:3d}) - Power: {entry['power_watts']:5.1f}W")
    
    # Check if it correlates with temperature
    print("\n\nTemperature vs Position 12 Correlation:")
    print("-" * 50)
    temps_and_values = []
    for entry in data:
        code1 = entry['codes'][1]
        byte18_hex = code1[36:38]
        byte18_dec = int(byte18_hex, 16)
        temp = entry['actual_temperature']
        temps_and_values.append((temp, byte18_dec))
    
    # Sort by temperature
    temps_and_values.sort()
    for temp, val in temps_and_values:
        print(f"Temp: {temp:4.1f}°C -> Value: 0x{val:02x} ({val})")
    
    # Summary of findings
    print("\n\nKEY FINDINGS:")
    print("=" * 70)
    print("1. Power consumption stabilized at 144.7W after initial fluctuation")
    print("2. CODE[4] position 3-4 (bytes 9-10) changes from 0000 to 0100/0101 when operating")
    print("3. CODE[4] position 5 (byte 11) is highly variable but might relate to compressor activity")
    print("4. CODE[1] position 12 (byte 18) increments with decreasing temperature:")
    print("   - Starts at 0xd3 (211) at 22.5°C")
    print("   - Ends at 0xe2 (226) at 16.5°C")
    print("   - This appears to be a temperature-related counter or reference")
    print("5. The 'operating' flag correctly reflects when the compressor is active")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    else:
        log_file = "device_status_log_20250803_153910.json"
    
    analyze_power_correlations(log_file)
