#!/usr/bin/env python3
"""
Compare Temperature Parsing

This script compares our temperature parsing with the homebridge implementation
using the exact same raw hex values.
"""

def get_normalized_temperature_homebridge(num):
    """Homebridge version of getNormalizedTemperature"""
    adjust_num = 5 * (num - int("80", 16))
    return 400 if adjust_num >= 400 else (0 if adjust_num <= 0 else adjust_num)

def get_normalized_temperature_ours(hex_value):
    """Our version of get_normalized_temperature"""
    adjusted = 5 * (hex_value - 0x80)
    if adjusted >= 400:
        return 400
    elif adjusted <= 0:
        return 0
    else:
        return adjusted

def test_temperature_parsing():
    """Test temperature parsing with actual hex values"""
    print("🔍 Comparing Temperature Parsing")
    print("=" * 50)
    
    # From our debug output:
    # Room temp raw: b0 = 176 (decimal)
    # Target temp raw: ad = 173 (decimal)
    # Outside temp raw: a8 = 168 (decimal)
    
    test_values = [
        ("Room Temperature", 0xb0, 176),
        ("Target Temperature", 0xad, 173), 
        ("Outside Temperature", 0xa8, 168)
    ]
    
    for name, hex_val, decimal_val in test_values:
        print(f"\n{name}:")
        print(f"  Raw hex: 0x{hex_val:02x} = {decimal_val}")
        
        # Test homebridge version
        homebridge_result = get_normalized_temperature_homebridge(decimal_val)
        print(f"  Homebridge result: {homebridge_result} = {homebridge_result / 10.0}°C")
        
        # Test our version
        our_result = get_normalized_temperature_ours(decimal_val)
        print(f"  Our result: {our_result} = {our_result / 10.0}°C")
        
        # Check if they match
        if homebridge_result == our_result:
            print(f"  ✅ Results match!")
        else:
            print(f"  ❌ Results differ!")
    
    # Also test the exact calculation step by step
    print(f"\n🔧 Step-by-step calculation for room temp (0xb0 = 176):")
    print(f"  176 - 128 (0x80) = {176 - 128}")
    print(f"  (176 - 128) * 5 = {(176 - 128) * 5}")
    print(f"  {(176 - 128) * 5} / 10.0 = {(176 - 128) * 5 / 10.0}°C")
    
    print(f"\n🔧 Step-by-step calculation for target temp (0xad = 173):")
    print(f"  173 - 128 (0x80) = {173 - 128}")
    print(f"  (173 - 128) * 5 = {(173 - 128) * 5}")
    print(f"  {(173 - 128) * 5} / 10.0 = {(173 - 128) * 5 / 10.0}°C")

if __name__ == "__main__":
    test_temperature_parsing()
