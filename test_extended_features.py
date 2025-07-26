#!/usr/bin/env python3

from ac_control import MitsubishiController
from mitsubishi_parser import VerticalWindDirection, HorizontalWindDirection

def test_extended_features():
    controller = MitsubishiController("192.168.0.54")
    
    print("Testing Extended AC Features")
    print("=" * 40)
    
    # Fetch current state first
    print("Fetching current state...")
    if not controller.fetch_status():
        print("❌ Failed to fetch device status")
        return
    
    print("✅ Current state fetched")
    
    # Test vertical vane control
    print("\n1. Testing vertical vane control (right side)...")
    result = controller.set_vertical_vane(VerticalWindDirection.V2, "right")
    print(f"✅ Vertical vane right result: {result}")
    
    print("\n2. Testing vertical vane control (left side)...")  
    result = controller.set_vertical_vane(VerticalWindDirection.V3, "left")
    print(f"✅ Vertical vane left result: {result}")
    
    # Test horizontal vane control
    print("\n3. Testing horizontal vane control...")
    result = controller.set_horizontal_vane(HorizontalWindDirection.L)
    print(f"✅ Horizontal vane result: {result}")
    
    # Test dehumidifier setting
    print("\n4. Testing dehumidifier setting...")
    result = controller.set_dehumidifier(80)
    print(f"✅ Dehumidifier result: {result}")
    
    # Test power saving mode
    print("\n5. Testing power saving mode...")
    result = controller.set_power_saving(True)
    print(f"✅ Power saving enable result: {result}")
    
    # Test buzzer control
    print("\n6. Testing buzzer control...")
    result = controller.send_buzzer_command(True)
    print(f"✅ Buzzer command result: {result}")
    
    print("\n7. Getting current status to verify changes...")
    controller.fetch_status()
    status = controller.get_status_summary()
    
    print("\nCurrent Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    test_extended_features()
