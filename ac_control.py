#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner Controller CLI

This script allows control and monitoring of Mitsubishi MAC-577IF-2E air conditioners
via command line using the new layered architecture.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from mitsubishi_api import MitsubishiAPI
from mitsubishi_controller import MitsubishiController
from mitsubishi_capabilities import CapabilityDetector, CapabilityType
from mitsubishi_parser import (
    PowerOnOff, DriveMode, WindSpeed, VerticalWindDirection, HorizontalWindDirection
)


def format_output(data, format_type):
    """Format data for output in various formats"""
    if format_type == 'json':
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    elif format_type == 'xml':
        # Convert dict to XML with full dynamic structure support
        root = ET.Element('response')
        _dict_to_xml_recursive(data, root)
        return ET.tostring(root, encoding='unicode')
    
    elif format_type == 'csv':
        # Flatten the data for CSV output
        flat_data = flatten_dict(data)
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(flat_data.keys())
        # Write values
        writer.writerow(flat_data.values())
        
        return output.getvalue().strip()
    
    else:  # table format (default)
        return format_table(data)


def _dict_to_xml_recursive(data, parent_element):
    """Recursively convert dictionary to XML elements"""
    if isinstance(data, dict):
        for key, value in data.items():
            element_name = str(key).replace(' ', '_').replace('-', '_')
            
            if isinstance(value, dict):
                sub_element = ET.SubElement(parent_element, element_name)
                _dict_to_xml_recursive(value, sub_element)
            elif isinstance(value, list):
                list_container = ET.SubElement(parent_element, element_name)
                for i, item in enumerate(value):
                    item_element = ET.SubElement(list_container, f"item_{i}")
                    _dict_to_xml_recursive(item, item_element)
            else:
                element = ET.SubElement(parent_element, element_name)
                element.text = str(value) if value is not None else ''


def flatten_dict(d, parent_key='', sep='_'):
    """Flatten nested dictionary for CSV output"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                items.append((f"{new_key}_{i}", str(item)))
        else:
            items.append((new_key, str(v) if v is not None else ''))
    return dict(items)


def format_table(data):
    """Format data as a readable table"""
    if not isinstance(data, dict):
        return str(data)
    
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key.upper()}:")
            lines.append("-" * len(key))
            for sub_key, sub_value in value.items():
                lines.append(f"  {sub_key}: {sub_value}")
            lines.append("")
        elif isinstance(value, list):
            lines.append(f"{key.upper()}: [{', '.join(str(item) for item in value)}]")
        else:
            lines.append(f"{key.upper()}: {value}")
    
    return '\n'.join(lines)


def main():
    """CLI interface for the Mitsubishi air conditioner controller"""
    parser = argparse.ArgumentParser(
        description='Control Mitsubishi MAC-577IF-2E air conditioner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --device-ip 192.168.0.54 --fetch-status
  %(prog)s --device-ip 192.168.0.54 --detect-capabilities
  %(prog)s --device-ip 192.168.0.54 --set-power on --set-temp 24.0
  %(prog)s --device-ip 192.168.0.54 --set-mode COOLER --set-fan-speed 2
"""
    )
    
    # Required arguments
    parser.add_argument('--device-ip', required=True, 
                       help='IP address of the air conditioner')
    
    # Output options
    parser.add_argument('--debug', action='store_true', 
                       help='Show debug information including raw requests/responses')
    parser.add_argument('--format', choices=['table', 'csv', 'json', 'xml'], 
                       default='json', help='Output format for data (default: json)')
    
    # Action arguments
    parser.add_argument('--fetch-status', action='store_true', 
                       help='Fetch and display device status')
    parser.add_argument('--detect-capabilities', action='store_true', 
                       help='Detect and display device capabilities')
    parser.add_argument('--enable-echonet', action='store_true', 
                       help='Send ECHONET enable command')
    
    # Control arguments
    parser.add_argument('--set-power', choices=['on', 'off'], 
                       help='Set power state')
    parser.add_argument('--set-temp', type=float, 
                       help='Set target temperature in Celsius')
    parser.add_argument('--set-mode', choices=[mode.name for mode in DriveMode], 
                       help='Set operating mode')
    parser.add_argument('--set-fan-speed', type=int, choices=[0, 1, 2, 3, 5], 
                       help='Set fan speed (0=auto, 1-3=levels, 5=full)')
    
    # Extended control arguments
    parser.add_argument('--set-vertical-vane', 
                       choices=[vane.name for vane in VerticalWindDirection],
                       help='Set vertical vane direction')
    parser.add_argument('--vane-side', choices=['left', 'right'], default='right',
                       help='Side for vertical vane control (default: right)')
    parser.add_argument('--set-horizontal-vane', 
                       choices=[vane.name for vane in HorizontalWindDirection],
                       help='Set horizontal vane direction')
    parser.add_argument('--set-dehumidifier', type=int, metavar='0-100',
                       help='Set dehumidifier level (0-100)')
    parser.add_argument('--set-power-saving', choices=['on', 'off'],
                       help='Enable or disable power saving mode')
    parser.add_argument('--send-buzzer', action='store_true',
                       help='Send buzzer command')
    
    args = parser.parse_args()
    
    # Initialize components
    api = MitsubishiAPI(device_ip=args.device_ip)
    controller = MitsubishiController(api=api)
    
    print(f"Mitsubishi Air Conditioner Controller - {args.device_ip}")
    print("=" * 60)
    
    try:
        # Handle capability detection
        if args.detect_capabilities:
            print("🔍 Detecting device capabilities...")
            detector = CapabilityDetector(api=api)
            capabilities = detector.detect_all_capabilities(debug=args.debug)
            
            output = format_output(capabilities.to_dict(), args.format)
            print(output)
            
            # Save capabilities to file
            detector.save_capabilities()
            return 0
        
        # Handle status fetching
        if args.fetch_status:
            print("📊 Fetching device status...")
            success = controller.fetch_status(debug=args.debug)
            
            if success:
                print("✅ Successfully fetched device status")
                
                # Get both structured state and summary
                status_data = {
                    'device_state': controller.state.to_dict() if hasattr(controller.state, 'to_dict') else {},
                    'status_summary': controller.get_status_summary()
                }
                
                output = format_output(status_data, args.format)
                print("\nDevice Status:")
                print("=" * 20)
                print(output)
            else:
                print("❌ Failed to fetch device status")
                return 1
        
        # Handle ECHONET enable command
        if args.enable_echonet:
            print("🌐 Enabling ECHONET...")
            success = controller.enable_echonet(debug=args.debug)
            
            if success:
                print("✅ ECHONET enable command sent successfully")
            else:
                print("❌ ECHONET enable command failed")
                return 1
        
        # Handle control commands
        control_executed = False
        
        # First fetch current state if any control command is specified
        control_commands = [
            args.set_power, args.set_temp, args.set_mode, args.set_fan_speed,
            args.set_vertical_vane, args.set_horizontal_vane, args.set_dehumidifier,
            args.set_power_saving, args.send_buzzer
        ]
        
        if any(cmd is not None for cmd in control_commands) or args.send_buzzer:
            print("📋 Fetching current device state for control operations...")
            if not controller.fetch_status(debug=args.debug):
                print("❌ Failed to fetch device status")
                return 1
            
            print("🎮 Executing control commands...")
        
        if args.set_power:
            print(f"⚡ Setting power {args.set_power.upper()}...")
            power_on = args.set_power.lower() == 'on'
            success = controller.set_power(power_on, debug=args.debug)
            print("✅ Power command sent" if success else "❌ Power command failed")
            control_executed = True
        
        if args.set_temp:
            print(f"🌡️  Setting temperature to {args.set_temp}°C...")
            success = controller.set_temperature(args.set_temp, debug=args.debug)
            print("✅ Temperature command sent" if success else "❌ Temperature command failed")
            control_executed = True
        
        if args.set_mode:
            print(f"🔄 Setting mode to {args.set_mode}...")
            mode = DriveMode[args.set_mode]
            success = controller.set_mode(mode, debug=args.debug)
            print("✅ Mode command sent" if success else "❌ Mode command failed")
            control_executed = True
        
        if args.set_fan_speed is not None:
            print(f"💨 Setting fan speed to {args.set_fan_speed}...")
            speed = WindSpeed(args.set_fan_speed)
            success = controller.set_fan_speed(speed, debug=args.debug)
            print("✅ Fan speed command sent" if success else "❌ Fan speed command failed")
            control_executed = True
        
        if args.set_vertical_vane:
            print(f"📐 Setting vertical vane ({args.vane_side}) to {args.set_vertical_vane}...")
            direction = VerticalWindDirection[args.set_vertical_vane]
            success = controller.set_vertical_vane(direction, args.vane_side, debug=args.debug)
            print("✅ Vertical vane command sent" if success else "❌ Vertical vane command failed")
            control_executed = True
        
        if args.set_horizontal_vane:
            print(f"↔️ Setting horizontal vane to {args.set_horizontal_vane}...")
            direction = HorizontalWindDirection[args.set_horizontal_vane]
            success = controller.set_horizontal_vane(direction, debug=args.debug)
            print("✅ Horizontal vane command sent" if success else "❌ Horizontal vane command failed")
            control_executed = True
        
        if args.set_dehumidifier is not None:
            if 0 <= args.set_dehumidifier <= 100:
                print(f"💧 Setting dehumidifier to {args.set_dehumidifier}%...")
                success = controller.set_dehumidifier(args.set_dehumidifier, debug=args.debug)
                print("✅ Dehumidifier command sent" if success else "❌ Dehumidifier command failed")
                control_executed = True
            else:
                print("❌ Dehumidifier level must be between 0-100")
                return 1
        
        if args.set_power_saving:
            power_saving_enabled = args.set_power_saving.lower() == 'on'
            print(f"⚡ Setting power saving mode {args.set_power_saving.upper()}...")
            success = controller.set_power_saving(power_saving_enabled, debug=args.debug)
            print("✅ Power saving command sent" if success else "❌ Power saving command failed")
            control_executed = True
        
        if args.send_buzzer:
            print("🔔 Sending buzzer command...")
            success = controller.send_buzzer_command(True, debug=args.debug)
            print("✅ Buzzer command sent" if success else "❌ Buzzer command failed")
            control_executed = True
        
        # If no specific action was requested, show basic status
        if not any([args.fetch_status, args.detect_capabilities, args.enable_echonet, control_executed]):
            print("ℹ️  No specific action requested. Fetching basic status...")
            success = controller.fetch_status(debug=args.debug)
            
            if success:
                summary = controller.get_status_summary()
                print("\nBasic Device Status:")
                print("=" * 25)
                for key, value in summary.items():
                    if key in ['mac', 'serial', 'power', 'mode', 'target_temp', 'room_temp']:
                        print(f"  {key}: {value}")
                
                print("\nUse --help to see all available options.")
            else:
                print("❌ Failed to connect to device")
                return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Operation interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1
    finally:
        # Always close the API connection
        api.close()


if __name__ == '__main__':
    exit(main())
