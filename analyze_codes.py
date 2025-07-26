#!/usr/bin/env python3
"""
Analyze the difference between profilecode and code values from Mitsubishi AC device
"""

from mitsubishi_parser import (
    is_general_states_payload, is_sensor_states_payload, is_error_states_payload,
    parse_general_states, parse_sensor_states, parse_error_states
)

def analyze_hex_payload(hex_value, payload_type="Unknown"):
    """Analyze a single hex payload and show what data it contains"""
    print(f"\n{'='*60}")
    print(f"Analyzing {payload_type}: {hex_value}")
    print(f"{'='*60}")
    
    if not hex_value or len(hex_value) < 20:
        print("❌ Payload too short to analyze")
        return
    
    hex_lower = hex_value.lower()
    
    # Show the payload structure
    print(f"Length: {len(hex_value)} characters")
    print(f"Hex structure breakdown:")
    print(f"  Positions 0-1:   {hex_value[0:2]}    (Header/Protocol)")
    print(f"  Positions 2-3:   {hex_value[2:4]}    (Command type)")
    print(f"  Positions 4-9:   {hex_value[4:10]}   (Address/routing)")
    print(f"  Positions 10-11: {hex_value[10:12]}  (Data type indicator)")
    print(f"  Positions 12+:   {hex_value[12:]}   (Payload data)")
    
    # Determine payload type
    if is_general_states_payload(hex_lower):
        print("\n✅ GENERAL STATES PAYLOAD (type 02)")
        states = parse_general_states(hex_lower)
        if states:
            print(f"  🔌 Power: {states.power_on_off.name}")
            print(f"  🌡️  Temperature: {states.temperature / 10.0}°C")
            print(f"  🏠 Mode: {states.drive_mode.name}")
            print(f"  💨 Fan Speed: {states.wind_speed.name}")
            print(f"  ↕️  Vertical Vane Right: {states.vertical_wind_direction_right.name}")
            print(f"  ↕️  Vertical Vane Left: {states.vertical_wind_direction_left.name}")
            print(f"  ↔️  Horizontal Vane: {states.horizontal_wind_direction.name}")
            print(f"  💧 Dehumidifier: {states.dehum_setting}")
            print(f"  ⚡ Power Saving: {states.is_power_saving}")
        
    elif is_sensor_states_payload(hex_lower):
        print("\n✅ SENSOR STATES PAYLOAD (type 03)")
        states = parse_sensor_states(hex_lower)
        if states:
            print(f"  🌡️  Room Temperature: {states.room_temperature / 10.0}°C")
            if states.outside_temperature:
                print(f"  🌤️  Outside Temperature: {states.outside_temperature / 10.0}°C")
            else:
                print(f"  🌤️  Outside Temperature: Not available")
            print(f"  📡 Thermal Sensor: {states.thermal_sensor}")
            print(f"  🔄 Wind Speed PR557: {states.wind_speed_pr557}")
        
    elif is_error_states_payload(hex_lower):
        print("\n✅ ERROR STATES PAYLOAD (type 04)")
        states = parse_error_states(hex_lower)
        if states:
            print(f"  ❌ Error State: {states.is_abnormal_state}")
            print(f"  🔢 Error Code: {states.error_code}")
        
    else:
        print("\n❓ UNKNOWN PAYLOAD TYPE")
        print("  This payload doesn't match any known patterns")
        print("  - Not general states (type 02)")
        print("  - Not sensor states (type 03)")
        print("  - Not error states (type 04)")

def main():
    print("🔍 MITSUBISHI AC CODE ANALYSIS")
    print("=" * 60)
    
    # Your actual device data from the JSON output
    profilecode_values = [
        "fc7b013010c9030020001407f58c25a0be94bea0be89",
        "fc7b013010cda0bea0bea0be041103b40a0000000087",
        "fc7b013010ce00000000000000000000000000000076",
        "fc7b013010cf0000000000002900000000000000004c",
        "fc7b013010d100000000000000000000000000000073"
    ]
    
    code_values = [
        "fc620130100200000103190001000085ad46000000c5",
        "fc620130100300000b00a0aaaafe42001195890000ec",
        "fc6201301004000000800000000000000000000000d9",
        "fc620130100500000000000000000000000000000058",
        "fc6201301006000000000004220300004200000000ec",
        "fc620130100900000001000000000000000000000053"
    ]
    
    print("\n📋 PROFILECODE VALUES ANALYSIS:")
    print("These appear to be device profile/configuration data")
    print("Notice they all start with 'fc7b' and have different endings")
    for i, code in enumerate(profilecode_values):
        analyze_hex_payload(code, f"PROFILECODE #{i+1}")
    
    print("\n\n📊 CODE VALUES ANALYSIS:")
    print("These contain the actual device state and sensor data")
    print("Notice they start with 'fc62' and have different type indicators")
    for i, code in enumerate(code_values):
        analyze_hex_payload(code, f"CODE #{i+1}")
    
    print("\n\n📝 SUMMARY:")
    print("=" * 60)
    print("🔑 KEY DIFFERENCES:")
    print("   PROFILECODE (fc7b): Device configuration/profile data")
    print("   CODE (fc62):        Live device state and sensor readings")
    print()
    print("🎯 WHAT WE USE:")
    print("   Our parser currently only uses CODE values (fc62)")
    print("   PROFILECODE values (fc7b) are likely configuration data")
    print("   that doesn't change frequently")
    print()
    print("🏆 THE RESULT:")
    print("   From the CODE values, we successfully extract:")
    print("   - Power state, temperature, mode, fan settings")
    print("   - Room and outside temperature readings")
    print("   - Error states and diagnostic information")

if __name__ == "__main__":
    main()
