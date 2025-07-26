#!/usr/bin/env python3

from ac_control import MitsubishiController
from mitsubishi_parser import DriveMode, WindSpeed, VerticalWindDirection, HorizontalWindDirection
import json

def restore_original_state():
    """Restore AC to its original state"""
    
    # Load original state
    with open('original_state.json', 'r') as f:
        original_state = json.load(f)
    
    controller = MitsubishiController("192.168.0.54")
    
    print("Restoring AC to Original State")
    print("=" * 40)
    
    # Fetch current state first
    print("Fetching current state...")
    if not controller.fetch_status():
        print("❌ Failed to fetch device status")
        return
    
    print("✅ Current state fetched")
    print("\nRestoring original settings...")
    
    # Restore power (should already be ON)
    if original_state["power"] == "ON":
        print("1. Setting power ON...")
        controller.set_power(True)
    
    # Restore mode
    mode_map = {
        'AUTO': DriveMode.AUTO,
        'COOLER': DriveMode.COOLER,
        'HEATER': DriveMode.HEATER,
        'DEHUM': DriveMode.DEHUM,
        'FAN': DriveMode.FAN
    }
    print(f"2. Setting mode to {original_state['mode']}...")
    controller.set_mode(mode_map[original_state["mode"]])
    
    # Restore temperature
    print(f"3. Setting temperature to {original_state['target_temp_celsius']}°C...")
    controller.set_temperature(original_state["target_temp_celsius"])
    
    # Restore fan speed
    speed_map = {
        'AUTO': WindSpeed.AUTO,
        'LEVEL_1': WindSpeed.LEVEL_1,
        'LEVEL_2': WindSpeed.LEVEL_2,
        'LEVEL_3': WindSpeed.LEVEL_3,
        'LEVEL_FULL': WindSpeed.LEVEL_FULL
    }
    print(f"4. Setting fan speed to {original_state['fan_speed']}...")
    controller.set_fan_speed(speed_map[original_state["fan_speed"]])
    
    # Restore vertical vane (right side)
    vane_map = {
        'AUTO': VerticalWindDirection.AUTO,
        'V1': VerticalWindDirection.V1,
        'V2': VerticalWindDirection.V2,
        'V3': VerticalWindDirection.V3,
        'V4': VerticalWindDirection.V4,
        'V5': VerticalWindDirection.V5,
        'SWING': VerticalWindDirection.SWING
    }
    print(f"5. Setting vertical vane (right) to {original_state['vertical_vane_right']}...")
    controller.set_vertical_vane(vane_map[original_state["vertical_vane_right"]], "right")
    
    # Restore horizontal vane
    horizontal_map = {
        'AUTO': HorizontalWindDirection.AUTO,
        'L': HorizontalWindDirection.L,
        'LS': HorizontalWindDirection.LS,
        'C': HorizontalWindDirection.C,
        'RS': HorizontalWindDirection.RS,
        'R': HorizontalWindDirection.R,
        'LC': HorizontalWindDirection.LC,
        'CR': HorizontalWindDirection.CR,
        'LR': HorizontalWindDirection.LR,
        'LCR': HorizontalWindDirection.LCR,
        'LCR_S': HorizontalWindDirection.LCR_S
    }
    print(f"6. Setting horizontal vane to {original_state['horizontal_vane']}...")
    controller.set_horizontal_vane(horizontal_map[original_state["horizontal_vane"]])
    
    # Restore dehumidifier setting
    print(f"7. Setting dehumidifier to {original_state['dehumidifier_setting']}...")
    controller.set_dehumidifier(original_state["dehumidifier_setting"])
    
    # Restore power saving mode
    print(f"8. Setting power saving mode to {original_state['power_saving_mode']}...")
    controller.set_power_saving(original_state["power_saving_mode"])
    
    print("\n✅ Restoration complete!")
    
    # Get final status
    print("\nVerifying restored state...")
    controller.fetch_status()
    status = controller.get_status_summary()
    
    print("\nFinal Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    restore_original_state()
