#!/usr/bin/env python3
"""
Debug Temperature Parsing

This script examines the raw response data to understand exactly 
how temperatures are being parsed and where the values come from.
"""

from mitsubishi_api import MitsubishiAPI
from mitsubishi_parser import parse_code_values
import xml.etree.ElementTree as ET

def debug_temperature_parsing():
    """Debug temperature parsing in detail"""
    print("🔍 Debugging Temperature Parsing")
    print("=" * 50)
    
    api = MitsubishiAPI(device_ip='192.168.0.54')
    
    # Get raw response
    response = api.send_status_request(debug=False)
    
    if response:
        try:
            root = ET.fromstring(response)
            
            # Extract CODE values
            code_values_elems = root.findall('.//CODE/VALUE')
            code_values = [elem.text for elem in code_values_elems if elem.text]
            
            print(f"📋 Found {len(code_values)} code values:")
            for i, code_value in enumerate(code_values):
                print(f"  CODE_{i}: {code_value}")
                
                # Analyze each code for temperature data
                if len(code_value) >= 42:
                    try:
                        # Check if this is a sensor states payload (group 03)
                        group_code = code_value[10:12]
                        if group_code == '03':
                            print(f"    📡 SENSOR DATA (Group 03):")
                            
                            # Parse temperature values according to our parser logic
                            outside_temp_raw = int(code_value[20:22], 16)
                            room_temp_raw = int(code_value[24:26], 16)
                            
                            print(f"      Outside temp raw (pos 20-22): {code_value[20:22]} = {outside_temp_raw}")
                            print(f"      Room temp raw (pos 24-26): {code_value[24:26]} = {room_temp_raw}")
                            
                            # Apply the get_normalized_temperature function logic
                            def get_normalized_temperature(hex_value):
                                adjusted = 5 * (hex_value - 0x80)
                                if adjusted >= 400:
                                    return 400
                                elif adjusted <= 0:
                                    return 0
                                else:
                                    return adjusted
                            
                            if outside_temp_raw >= 16:
                                outside_temp = get_normalized_temperature(outside_temp_raw)
                                print(f"      Outside temp calculated: {outside_temp / 10.0}°C")
                            
                            room_temp = get_normalized_temperature(room_temp_raw)
                            print(f"      Room temp calculated: {room_temp / 10.0}°C")
                            
                        elif group_code == '02':
                            print(f"    🎛️  GENERAL STATES (Group 02):")
                            
                            # Parse target temperature (position 32-34)
                            target_temp_raw = int(code_value[32:34], 16)
                            print(f"      Target temp raw (pos 32-34): {code_value[32:34]} = {target_temp_raw}")
                            
                            # Apply the get_normalized_temperature function logic
                            def get_normalized_temperature(hex_value):
                                adjusted = 5 * (hex_value - 0x80)
                                if adjusted >= 400:
                                    return 400
                                elif adjusted <= 0:
                                    return 0
                                else:
                                    return adjusted
                            
                            target_temp = get_normalized_temperature(target_temp_raw)
                            print(f"      Target temp calculated: {target_temp / 10.0}°C")
                            
                    except (ValueError, IndexError) as e:
                        print(f"    ❌ Error parsing: {e}")
                print()
            
            # Now parse using our existing system
            print("🔧 Using Our Parser System:")
            print("-" * 30)
            parsed_state = parse_code_values(code_values)
            
            if parsed_state.general:
                print(f"General State Target Temp: {parsed_state.general.temperature / 10.0}°C")
            
            if parsed_state.sensors:
                print(f"Sensor Room Temp: {parsed_state.sensors.room_temperature / 10.0}°C")
                if parsed_state.sensors.outside_temperature:
                    print(f"Sensor Outside Temp: {parsed_state.sensors.outside_temperature / 10.0}°C")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    api.close()

if __name__ == "__main__":
    debug_temperature_parsing()
