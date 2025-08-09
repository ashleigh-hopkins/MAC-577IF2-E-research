#!/usr/bin/env python3
"""
FC Temperature Decoder - Advanced analysis of temperature data in FC messages

This script focuses on decoding temperature and sensor readings from the FC messages.
"""

import sys
from pathlib import Path

# Import our parser
from fc_message_parser import FCMessageParser, parse_fc_logs

def decode_temperature_from_hex(hex_val):
    """Convert hex temperature value to Celsius using Mitsubishi's format"""
    val = int(hex_val, 16)
    
    # Based on mitsubishi_parser.py logic
    if val >= 0x80:
        # Temperature format: normalized = 5 * (val - 0x80)
        normalized = 5 * (val - 0x80)
        celsius = normalized / 10.0
        return celsius
    return None

def analyze_type3_temperature_patterns():
    """Detailed analysis of Type 3 temperature messages"""
    
    # Sample Type 3 messages showing temperature changes
    type3_samples = [
        # Early messages with AE AE pattern
        "62 01 30 10 03 00 00 0d 00 ac ae ae fe 42 00 11 c1 a4 00 00 8f 00 00 00 00",
        # Transition to AE AD pattern  
        "62 01 30 10 03 00 00 0d 00 ac ae ad fe 42 00 11 c1 a4 00 00 90 00 00 00 00",
        # Change to AD AD pattern and byte 7 changes to 0c
        "62 01 30 10 03 00 00 0c 00 ac ad ad fe 42 00 11 c1 a5 00 00 91 00 00 00 00",
        # Back to AE pattern
        "62 01 30 10 03 00 00 0c 00 ac ad ae fe 42 00 11 c1 a5 00 00 90 00 00 00 00",
        # Final change back to AE AE with byte 7 = 0d
        "62 01 30 10 03 00 00 0d 00 ac ae ae fe 42 00 11 c1 a5 00 00 8e 00 00 00 00",
    ]
    
    print("Type 3 Temperature Message Analysis")
    print("=" * 50)
    
    for i, payload in enumerate(type3_samples):
        print(f"\nSample {i+1}: {payload}")
        bytes_array = payload.split()
        
        # Key temperature-related positions
        byte7 = bytes_array[7]    # 0c/0d - seems to be a temperature flag
        byte10 = bytes_array[10]  # ac - constant
        byte11 = bytes_array[11]  # ae/ad - temperature reading 1
        byte12 = bytes_array[12]  # ae/ad - temperature reading 2  
        byte13 = bytes_array[13]  # fe - constant
        byte17 = bytes_array[17]  # a4/a5 - another temperature/setpoint
        byte21 = bytes_array[21]  # 8f/90/91 - varies with other bytes
        
        print(f"  Byte 7 (flag):     0x{byte7} = {int(byte7, 16)}")
        print(f"  Byte 10 (const):   0x{byte10} = {int(byte10, 16)}")
        print(f"  Byte 11 (temp1):   0x{byte11} = {int(byte11, 16)} -> {decode_temperature_from_hex(byte11):.1f}°C")
        print(f"  Byte 12 (temp2):   0x{byte12} = {int(byte12, 16)} -> {decode_temperature_from_hex(byte12):.1f}°C")
        print(f"  Byte 13 (const):   0x{byte13} = {int(byte13, 16)}")
        print(f"  Byte 17 (setpoint): 0x{byte17} = {int(byte17, 16)} -> {decode_temperature_from_hex(byte17):.1f}°C")
        print(f"  Byte 21 (checksum): 0x{byte21} = {int(byte21, 16)}")

def analyze_type2_status_messages():
    """Analyze Type 2 status messages for power/mode info"""
    
    # Type 2 message sample
    type2_sample = "62 01 30 10 02 00 00 01 03 07 00 01 00 00 85 b0 28 00 00 00 f2 00 00 00 00"
    
    print("\n\nType 2 Status Message Analysis")
    print("=" * 50)
    print(f"Sample: {type2_sample}")
    
    bytes_array = type2_sample.split()
    
    # Key status positions based on our earlier analysis
    byte7 = bytes_array[7]    # Power status (01 = ON)
    byte8 = bytes_array[8]    # Mode (03 = COOLER based on mitsubishi_parser)
    byte9 = bytes_array[9]    # Fan speed (07)
    byte11 = bytes_array[11]  # Another flag (01)
    
    print(f"  Byte 7 (power):    0x{byte7} = {int(byte7, 16)} -> {'ON' if int(byte7, 16) == 1 else 'OFF'}")
    print(f"  Byte 8 (mode):     0x{byte8} = {int(byte8, 16)} -> COOLER (based on mitsubishi_parser)")
    print(f"  Byte 9 (fan):      0x{byte9} = {int(byte9, 16)} -> Fan level {int(byte9, 16)}")
    print(f"  Byte 11 (flag):    0x{byte11} = {int(byte11, 16)}")

def analyze_type6_sensor_messages():
    """Analyze Type 6 sensor messages"""
    
    type6_sample = "62 01 30 10 06 00 00 00 00 00 04 22 47 00 00 42 00 00 00 00 a8 00 00 00 00"
    
    print("\n\nType 6 Sensor Message Analysis")
    print("=" * 50)
    print(f"Sample: {type6_sample}")
    
    bytes_array = type6_sample.split()
    
    # Look for interesting sensor data
    byte10 = bytes_array[10]  # 04
    byte11 = bytes_array[11]  # 22 = 34 decimal
    byte12 = bytes_array[12]  # 47 = 71 decimal
    byte15 = bytes_array[15]  # 42 = 66 decimal
    byte20 = bytes_array[20]  # a8 = 168 decimal
    
    print(f"  Byte 10: 0x{byte10} = {int(byte10, 16)}")
    print(f"  Byte 11: 0x{byte11} = {int(byte11, 16)} (could be humidity: {int(byte11, 16)}%)")
    print(f"  Byte 12: 0x{byte12} = {int(byte12, 16)} (could be sensor reading)")
    print(f"  Byte 15: 0x{byte15} = {int(byte15, 16)} (could be another sensor)")
    print(f"  Byte 20: 0x{byte20} = {int(byte20, 16)} -> {decode_temperature_from_hex(byte20):.1f}°C (if temperature)")

def summarize_findings():
    """Summarize key findings about FC message structure"""
    
    print("\n\nKey Findings Summary")
    print("=" * 50)
    print("1. MESSAGE STRUCTURE:")
    print("   - Bytes 0-4: Header (62/42, 01, 30, 10, command_type)")
    print("   - Bytes 5-6: Usually 00 00")
    print("   - Bytes 7+: Command-specific data")
    print()
    print("2. TYPE 2 (Status Messages):")
    print("   - Byte 7: Power status (00=OFF, 01=ON)")
    print("   - Byte 8: Operating mode (03=COOLER, etc.)")
    print("   - Byte 9: Fan speed level")
    print()
    print("3. TYPE 3 (Temperature Messages):")
    print("   - Byte 7: Temperature flag (0C/0D)")
    print("   - Bytes 11-12: Room temperature readings (AE/AD = ~23.0°C/22.5°C)")
    print("   - Byte 17: Setpoint temperature (A4/A5 = ~18.0°C/18.5°C)")
    print("   - Pattern: AE AE -> AE AD -> AD AD -> AD AE -> AE AE")
    print()
    print("4. TYPE 6 (Sensor Messages):")
    print("   - Byte 11: Possibly humidity (22 = 34%)")
    print("   - Byte 12: Additional sensor reading")
    print()
    print("5. POLLING PATTERN:")
    print("   - System polls: Type 5 -> 3 -> 4 -> 6 -> 9 -> 2, then repeats")
    print("   - Temperature changes are gradual (AE->AD = ~0.5°C steps)")

def main():
    print("Advanced FC Message Temperature Decoder")
    print("=" * 60)
    
    analyze_type3_temperature_patterns()
    analyze_type2_status_messages() 
    analyze_type6_sensor_messages()
    summarize_findings()
    
    print("\n\nNext Steps:")
    print("- Monitor FC messages during temperature changes")
    print("- Correlate with actual room temperature readings")
    print("- Test AC control commands to see request/response patterns")

if __name__ == '__main__':
    main()
