#!/usr/bin/env python3
"""
Analyze hex code changes in device status log, excluding temperature-related bytes.
This script focuses on identifying bytes that change and might relate to power consumption.
"""

import json
import sys
from typing import List, Dict, Any

def load_log_data(filename: str) -> List[Dict[str, Any]]:
    """Load log data from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def hex_to_bytes(hex_string: str) -> List[str]:
    """Convert hex string to list of byte pairs."""
    # Remove 'fc' prefix and split into byte pairs
    clean_hex = hex_string[2:] if hex_string.startswith('fc') else hex_string
    return [clean_hex[i:i+2] for i in range(0, len(clean_hex), 2)]

def analyze_code_changes(data: List[Dict[str, Any]]) -> Dict[str, Dict[int, List[str]]]:
    """Analyze which bytes change in each code group across iterations."""
    code_changes = {}
    
    # Process each code index (0-5 for codes)
    for code_idx in range(6):  # Assuming 6 code entries
        code_changes[f"CODE[{code_idx}]"] = {}
        
        # Get all hex strings for this code index across iterations
        code_strings = []
        for iteration in data:
            if code_idx < len(iteration['codes']):
                code_strings.append(iteration['codes'][code_idx])
        
        if not code_strings:
            continue
            
        # Convert to byte arrays
        byte_arrays = [hex_to_bytes(code) for code in code_strings]
        
        # Find bytes that change
        if byte_arrays:
            max_length = max(len(arr) for arr in byte_arrays)
            
            for byte_pos in range(max_length):
                values_at_pos = []
                for arr in byte_arrays:
                    if byte_pos < len(arr):
                        values_at_pos.append(arr[byte_pos])
                    else:
                        values_at_pos.append('--')
                
                # Check if this byte position has variations
                unique_values = set(values_at_pos)
                if len(unique_values) > 1:
                    code_changes[f"CODE[{code_idx}]"][byte_pos] = values_at_pos
    
    return code_changes

def analyze_profilecode_changes(data: List[Dict[str, Any]]) -> Dict[str, Dict[int, List[str]]]:
    """Analyze which bytes change in each profilecode group across iterations."""
    profilecode_changes = {}
    
    # Process each profilecode index
    for profile_idx in range(5):  # Assuming 5 profilecode entries
        profilecode_changes[f"PROFILE[{profile_idx}]"] = {}
        
        # Get all hex strings for this profilecode index across iterations
        profile_strings = []
        for iteration in data:
            if profile_idx < len(iteration['profilecodes']):
                profile_strings.append(iteration['profilecodes'][profile_idx])
        
        if not profile_strings:
            continue
            
        # Convert to byte arrays
        byte_arrays = [hex_to_bytes(profile) for profile in profile_strings]
        
        # Find bytes that change
        if byte_arrays:
            max_length = max(len(arr) for arr in byte_arrays)
            
            for byte_pos in range(max_length):
                values_at_pos = []
                for arr in byte_arrays:
                    if byte_pos < len(arr):
                        values_at_pos.append(arr[byte_pos])
                    else:
                        values_at_pos.append('--')
                
                # Check if this byte position has variations
                unique_values = set(values_at_pos)
                if len(unique_values) > 1:
                    profilecode_changes[f"PROFILE[{profile_idx}]"][byte_pos] = values_at_pos
    
    return profilecode_changes

def identify_temperature_bytes(data: List[Dict[str, Any]], code_changes: Dict[str, Dict[int, List[str]]]) -> Dict[str, List[int]]:
    """Identify likely temperature-related bytes by correlating with set/actual temperatures."""
    temp_bytes = {}
    
    # Extract temperature values from iterations
    set_temps = [entry['set_temperature'] for entry in data]
    actual_temps = [entry['actual_temperature'] for entry in data]
    
    print(f"Temperature progression:")
    print(f"Set temperatures: {set_temps}")
    print(f"Actual temperatures: {actual_temps}")
    
    # Look for bytes that correlate with temperature changes
    for code_group, byte_changes in code_changes.items():
        temp_bytes[code_group] = []
        
        for byte_pos, values in byte_changes.items():
            # Convert hex values to decimal for correlation analysis
            decimal_values = []
            for hex_val in values:
                if hex_val != '--':
                    try:
                        decimal_values.append(int(hex_val, 16))
                    except ValueError:
                        decimal_values.append(0)
                else:
                    decimal_values.append(0)
            
            # Check for correlation with temperature (simple heuristic)
            # If values decrease as temperature decreases, likely temperature-related
            if len(decimal_values) > 1 and len(set(decimal_values)) > 1:
                # Check if values generally decrease with temperature
                temp_correlated = True
                for i in range(1, len(decimal_values)):
                    if i < len(set_temps) and decimal_values[i] != decimal_values[i-1]:
                        # This is a simple heuristic - could be refined
                        pass
                
                # For now, flag bytes that change systematically
                if len(set(decimal_values)) == len(decimal_values) or len(set(decimal_values)) > len(decimal_values) // 2:
                    temp_bytes[code_group].append(byte_pos)
    
    return temp_bytes

def print_analysis(code_changes: Dict[str, Dict[int, List[str]]], 
                  profilecode_changes: Dict[str, Dict[int, List[str]]],
                  temp_bytes: Dict[str, List[int]],
                  data: List[Dict[str, Any]]):
    """Print detailed analysis of hex changes."""
    
    print("="*80)
    print("HEX CODE ANALYSIS - EXCLUDING TEMPERATURE BYTES")
    print("="*80)
    
    print(f"\nAnalyzed {len(data)} iterations")
    print(f"Temperature range: {min(entry['set_temperature'] for entry in data)}°C to {max(entry['set_temperature'] for entry in data)}°C")
    print(f"Power consumption range: {min(entry['power_watts'] for entry in data)}W to {max(entry['power_watts'] for entry in data)}W")
    print(f"Operating status: {[entry['operating'] for entry in data]}")
    
    print("\n" + "="*60)
    print("CODE CHANGES (excluding likely temperature bytes)")
    print("="*60)
    
    for code_group, byte_changes in code_changes.items():
        if byte_changes:
            print(f"\n{code_group}:")
            temp_related = temp_bytes.get(code_group, [])
            
            for byte_pos, values in sorted(byte_changes.items()):
                if byte_pos in temp_related:
                    print(f"  Byte {byte_pos:2d}: {' -> '.join(values)} (LIKELY TEMPERATURE)")
                else:
                    print(f"  Byte {byte_pos:2d}: {' -> '.join(values)}")
                    
                    # Show decimal values for non-temperature bytes
                    decimal_vals = []
                    for hex_val in values:
                        if hex_val != '--':
                            try:
                                decimal_vals.append(str(int(hex_val, 16)))
                            except ValueError:
                                decimal_vals.append('??')
                        else:
                            decimal_vals.append('--')
                    print(f"              Decimal: {' -> '.join(decimal_vals)}")
    
    print("\n" + "="*60)
    print("PROFILECODE CHANGES")
    print("="*60)
    
    if any(profilecode_changes.values()):
        for profile_group, byte_changes in profilecode_changes.items():
            if byte_changes:
                print(f"\n{profile_group}:")
                for byte_pos, values in sorted(byte_changes.items()):
                    print(f"  Byte {byte_pos:2d}: {' -> '.join(values)}")
                    
                    # Show decimal values
                    decimal_vals = []
                    for hex_val in values:
                        if hex_val != '--':
                            try:
                                decimal_vals.append(str(int(hex_val, 16)))
                            except ValueError:
                                decimal_vals.append('??')
                        else:
                            decimal_vals.append('--')
                    print(f"              Decimal: {' -> '.join(decimal_vals)}")
    else:
        print("\nNo changes detected in PROFILECODE entries across all iterations.")
    
    print("\n" + "="*60)
    print("POTENTIAL ENERGY-RELATED BYTES")
    print("="*60)
    
    # Highlight bytes that might correlate with energy consumption
    power_values = [entry['power_watts'] for entry in data]
    operating_values = [entry['operating'] for entry in data]
    
    print(f"\nPower consumption: {' -> '.join(map(str, power_values))}")
    print(f"Operating status: {' -> '.join(map(str, operating_values))}")
    
    # Look for bytes that change when operating status changes
    operating_change_iteration = None
    for i, operating in enumerate(operating_values):
        if i > 0 and operating != operating_values[i-1]:
            operating_change_iteration = i
            break
    
    if operating_change_iteration:
        print(f"\nOperating status changed at iteration {operating_change_iteration}")
        print("Bytes that changed at the same time (potential energy indicators):")
        
        for code_group, byte_changes in code_changes.items():
            temp_related = temp_bytes.get(code_group, [])
            for byte_pos, values in byte_changes.items():
                if byte_pos not in temp_related and operating_change_iteration < len(values):
                    if (operating_change_iteration > 0 and 
                        values[operating_change_iteration] != values[operating_change_iteration-1]):
                        print(f"  {code_group} Byte {byte_pos}: {values[operating_change_iteration-1]} -> {values[operating_change_iteration]}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_hex_changes.py <log_file.json>")
        sys.exit(1)
    
    log_file = sys.argv[1]
    
    try:
        data = load_log_data(log_file)
        code_changes = analyze_code_changes(data)
        profilecode_changes = analyze_profilecode_changes(data)
        temp_bytes = identify_temperature_bytes(data, code_changes)
        
        print_analysis(code_changes, profilecode_changes, temp_bytes, data)
        
    except FileNotFoundError:
        print(f"Error: Log file '{log_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in log file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
