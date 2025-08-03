#!/usr/bin/env python3
"""
Temperature Range Detection Test

This script tests temperature range detection from ProfileCode data and compares
with known standards from various sources.
"""

from mitsubishi_api import MitsubishiAPI
from mitsubishi_capabilities import CapabilityDetector

def test_with_real_device():
    """Test temperature range detection with real device data"""
    print("🌡️ Testing Temperature Range Detection")
    print("=" * 60)
    
    # Known temperature ranges from different sources
    known_ranges = {
        "SwiCago HeatPump Library": {
            "min": 16,
            "max": 31,
            "source": "TEMP_MAP[16] = {31, 30, 29, ..., 17, 16}",
            "citation": "https://github.com/SwiCago/HeatPump"
        },
        "Our Parser Implementation": {
            "min": 16,
            "max": 31,
            "source": "MIN_TEMPERATURE = 160 (16.0°C), MAX_TEMPERATURE = 310 (31.0°C)",
            "citation": "mitsubishi_parser.py lines 14-15"
        },
        "Homebridge Plugin": {
            "min": 16,
            "max": 31,
            "source": "minValue: 16, maxValue: 31, minStep: 0.5",
            "citation": "homebridge-mitsubishi-electric-aircon MEAirconPlatformAccessory.ts"
        },
        "Meldec Group 13 Example": {
            "min": 17,
            "max": 31,
            "source": "fc62027a1013010011001f... -> step=1°C, min=17°C, max=31°C",
            "citation": "meldec/examples/decoded_request_xml line 170"
        }
    }
    
    print("📚 Known Temperature Ranges from Literature:")
    for source, data in known_ranges.items():
        print(f"  {source}:")
        print(f"    Range: {data['min']}°C - {data['max']}°C")
        print(f"    Source: {data['source']}")
        print(f"    Citation: {data['citation']}")
        print()
    
    # Test with real device
    print("📡 Testing with Real Device:")
    try:
        api = MitsubishiAPI(device_ip='192.168.0.54')
        detector = CapabilityDetector(api)
        
        # Get capabilities
        capabilities = detector.detect_all_capabilities(debug=True)
        
        # Check if we have temperature control capability
        temp_capability = capabilities.get_capability('temperature_control')
        if temp_capability:
            print(f"✅ Temperature Control Detected:")
            print(f"   Min: {temp_capability.min_value}°C")
            print(f"   Max: {temp_capability.max_value}°C")
            print(f"   Metadata: {temp_capability.metadata}")
        else:
            print("❌ No temperature control capability detected")
        
        # Analyze ProfileCode for temperature range hints
        print("\n🔍 ProfileCode Analysis for Temperature Hints:")
        if capabilities.profile_codes:
            for profile_key, profile_hex in capabilities.profile_codes.items():
                print(f"\n{profile_key}: {profile_hex}")
                analyze_profile_for_temperature_hints(profile_hex)
        
        # Check group codes for temperature-related data
        print(f"\n📊 Supported Group Codes: {sorted(capabilities.supported_group_codes)}")
        temperature_related_groups = ['02', '03', '09', '13', '1a', '26']
        found_temp_groups = [g for g in temperature_related_groups if g in capabilities.supported_group_codes]
        if found_temp_groups:
            print(f"🌡️ Temperature-related groups found: {found_temp_groups}")
            print("   Group 02: General states (includes current temperature)")
            print("   Group 03: Sensor states (room/outdoor temperature)")
            print("   Group 09: Temperature setpoints")
            print("   Group 13: Temperature range configuration")
            print("   Group 1a: Advanced temperature settings")
            print("   Group 26: Hot water temperature (heat pumps)")
        
    except Exception as e:
        print(f"❌ Error testing with real device: {e}")
    
    print("\n🎯 Conclusion:")
    print("Based on multiple sources, the standard Mitsubishi temperature range is:")
    print("   • Minimum: 16°C")
    print("   • Maximum: 31°C") 
    print("   • Step: 0.5°C or 1°C (depending on model)")
    print("   • Some heat pump models may support 17°C-31°C range")

def analyze_profile_for_temperature_hints(profile_hex):
    """Analyze a ProfileCode for temperature-related hints"""
    try:
        data = bytes.fromhex(profile_hex)
        if len(data) < 22:
            print(f"   ⚠️ Profile too short: {len(data)} bytes")
            return
        
        # Extract key fields
        group_code = data[5]
        payload = data[6:20]
        
        print(f"   Group Code: 0x{group_code:02x}")
        
        if group_code == 0xc9:  # Main capability descriptor
            version_info = int.from_bytes(payload[0:2], 'big')
            feature_flags = int.from_bytes(payload[2:4], 'big')
            capability_field = int.from_bytes(payload[4:6], 'big')
            
            print(f"   Version Info: 0x{version_info:04x}")
            print(f"   Feature Flags: 0x{feature_flags:04x}")
            print(f"   Capability Field: 0x{capability_field:04x}")
            
            # Look for temperature-related capability bits
            temp_bits = []
            if capability_field & 0x0007:  # Lower 3 bits often temperature modes
                temp_bits.append("temperature_modes")
            if capability_field & 0x0070:  # Bits 4-6 might be range related
                temp_bits.append("temperature_range_extended")
            if capability_field & 0x1400:  # Common extended feature bits
                temp_bits.append("advanced_temperature_features")
            
            if temp_bits:
                print(f"   🌡️ Temperature-related capabilities: {temp_bits}")
            
        elif group_code == 0x13:  # Temperature range group (from meldec)
            # Parse as temperature range configuration
            if len(payload) >= 6:
                step = payload[0]
                min_temp = payload[2] 
                max_temp = payload[4]
                print(f"   🌡️ Temperature Range Config: step={step}°C, min={min_temp}°C, max={max_temp}°C")
        
    except Exception as e:
        print(f"   ❌ Error analyzing profile: {e}")

if __name__ == "__main__":
    test_with_real_device()
