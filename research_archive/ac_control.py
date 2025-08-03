#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner Controller CLI

This script allows control and monitoring of Mitsubishi MAC-577IF-2E air conditioners
via command line using the new layered architecture.
"""

import argparse
import json
import sys
import os
import xml.etree.ElementTree as ET

# Add the local pymitsubishi directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../pymitsubishi'))

from pymitsubishi import MitsubishiAPI, MitsubishiController
from pymitsubishi.mitsubishi_capabilities import CapabilityDetector
from pymitsubishi.mitsubishi_parser import (
    DriveMode, WindSpeed, VerticalWindDirection, HorizontalWindDirection
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
        return format_table(data, indent=2)


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


def format_table(data, indent=0):
    """Format data as a readable table with improved formatting"""
    if not isinstance(data, dict):
        return str(data)
    
    lines = []
    base_indent = " " * indent
    
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{base_indent}{key.replace('_', ' ').title()}:")
            lines.append(f"{base_indent}{"-" * (len(key) + 1)}")
            # Format nested dictionaries with better structure
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict):
                    lines.append(f"{base_indent}  {sub_key.replace('_', ' ').title()}:")
                    for nested_key, nested_value in sub_value.items():
                        lines.append(f"{base_indent}    {nested_key}: {nested_value}")
                elif isinstance(sub_value, list) and len(sub_value) > 3:
                    lines.append(f"{base_indent}  {sub_key.replace('_', ' ').title()}: [{len(sub_value)} items]")
                elif isinstance(sub_value, list):
                    lines.append(f"{base_indent}  {sub_key.replace('_', ' ').title()}: [{', '.join(str(item) for item in sub_value)}]")
                else:
                    lines.append(f"{base_indent}  {sub_key.replace('_', ' ').title()}: {sub_value}")
            lines.append("")
        elif isinstance(value, list) and len(value) > 3:
            lines.append(f"{base_indent}{key.replace('_', ' ').title()}: [{len(value)} items]")
        elif isinstance(value, list):
            lines.append(f"{base_indent}{key.replace('_', ' ').title()}: [{', '.join(str(item) for item in value)}]")
        else:
            lines.append(f"{base_indent}{key.replace('_', ' ').title()}: {value}")
    
    return '\n'.join(lines)


def _analyze_all_undocumented_patterns(api, debug=False):
    """Analyze undocumented patterns from all code entries and profilecodes in the raw response"""
    try:
        # Get raw response from the API
        response = api.send_status_request(debug=debug)
        if not response:
            return None
            
        # Parse the XML response
        root = ET.fromstring(response)
        
        analysis_result = {
            'total_codes_analyzed': 0,
            'total_profilecodes_analyzed': 0,
            'combined_analysis': {
                'all_high_bits_patterns': [],
                'all_suspicious_patterns': [],
                'all_unknown_segments': {},
                'pattern_frequency': {},
                'profilecode_analysis': []
            }
        }
        
        # Import the analyze_undocumented_bits function from the parser
        from pymitsubishi.mitsubishi_parser import analyze_undocumented_bits
        
        # Analyze all CODE entries
        code_values_elems = root.findall('.//CODE/DATA/VALUE') or root.findall('.//CODE/VALUE')
        code_values = [elem.text for elem in code_values_elems if elem.text]
        
        for i, code_value in enumerate(code_values):
            if code_value and len(code_value) >= 42:
                code_analysis = analyze_undocumented_bits(code_value)
                analysis_result['total_codes_analyzed'] += 1
                
                # Aggregate high bits patterns
                if code_analysis.get('high_bits_set'):
                    for high_bit in code_analysis['high_bits_set']:
                        pattern_key = f"pos_{high_bit['position']}_val_{high_bit['hex']}"
                        analysis_result['combined_analysis']['all_high_bits_patterns'].append({
                            'code_index': i,
                            'position': high_bit['position'],
                            'hex': high_bit['hex'],
                            'value': high_bit['value'],
                            'binary': high_bit['binary']
                        })
                        
                        # Track frequency
                        freq_key = f"high_bit_pos_{high_bit['position']}"
                        analysis_result['combined_analysis']['pattern_frequency'][freq_key] = \
                            analysis_result['combined_analysis']['pattern_frequency'].get(freq_key, 0) + 1
                
                # Aggregate suspicious patterns
                if code_analysis.get('suspicious_patterns'):
                    for suspicious in code_analysis['suspicious_patterns']:
                        analysis_result['combined_analysis']['all_suspicious_patterns'].append({
                            'code_index': i,
                            'type': suspicious['type'],
                            'position': suspicious['position'],
                            'hex': suspicious['hex'],
                            'value': suspicious['value'],
                            'possible_i_see': suspicious.get('possible_i_see', False)
                        })
                
                # Aggregate unknown segments
                if code_analysis.get('unknown_segments'):
                    for pos, segment_data in code_analysis['unknown_segments'].items():
                        segment_key = f"code_{i}_pos_{pos}"
                        analysis_result['combined_analysis']['all_unknown_segments'][segment_key] = {
                            'code_index': i,
                            'position': pos,
                            'hex': segment_data['hex'],
                            'value': segment_data['value'],
                            'binary': segment_data['binary']
                        }
        
        # Analyze PROFILECODE entries
        profile_elems = root.findall('.//PROFILECODE/DATA/VALUE') or root.findall('.//PROFILECODE/VALUE')
        
        for i, profile_elem in enumerate(profile_elems):
            if profile_elem.text and len(profile_elem.text) >= 10:
                profile_value = profile_elem.text
                analysis_result['total_profilecodes_analyzed'] += 1
                
                # Analyze each profilecode for patterns
                profile_analysis = {
                    'profilecode_index': i,
                    'length': len(profile_value),
                    'raw_value': profile_value,
                    'byte_analysis': []
                }
                
                # Parse profilecode as hex and analyze byte patterns
                try:
                    for j in range(0, min(len(profile_value), 52), 2):  # Analyze up to 26 bytes
                        if j + 2 <= len(profile_value):
                            byte_hex = profile_value[j:j+2]
                            byte_val = int(byte_hex, 16)
                            
                            byte_info = {
                                'position': j // 2,
                                'hex': byte_hex,
                                'value': byte_val,
                                'binary': f"{byte_val:08b}",
                                'high_bit_set': bool(byte_val & 0x80)
                            }
                            
                            profile_analysis['byte_analysis'].append(byte_info)
                            
                            # Track high bit patterns in profilecodes too
                            if byte_val & 0x80:
                                freq_key = f"profile_high_bit_pos_{j//2}"
                                analysis_result['combined_analysis']['pattern_frequency'][freq_key] = \
                                    analysis_result['combined_analysis']['pattern_frequency'].get(freq_key, 0) + 1
                                    
                except ValueError:
                    profile_analysis['parse_error'] = f"Invalid hex in profilecode: {profile_value}"
                
                analysis_result['combined_analysis']['profilecode_analysis'].append(profile_analysis)
        
        # Add summary statistics
        analysis_result['summary'] = {
            'total_high_bit_patterns': len(analysis_result['combined_analysis']['all_high_bits_patterns']),
            'total_suspicious_patterns': len(analysis_result['combined_analysis']['all_suspicious_patterns']),
            'total_unknown_segments': len(analysis_result['combined_analysis']['all_unknown_segments']),
            'most_frequent_patterns': sorted(
                analysis_result['combined_analysis']['pattern_frequency'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]  # Top 10 most frequent patterns
        }
        
        if debug:
            print(f"🔍 Analyzed {analysis_result['total_codes_analyzed']} code entries and {analysis_result['total_profilecodes_analyzed']} profilecode entries")
            print(f"📊 Found {analysis_result['summary']['total_high_bit_patterns']} high bit patterns, {analysis_result['summary']['total_suspicious_patterns']} suspicious patterns")
        
        return analysis_result
        
    except Exception as e:
        if debug:
            print(f"⚠️ Error in comprehensive undocumented analysis: {e}")
        return None


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
    parser.add_argument('--include-capabilities', action='store_true',
                       help='Include capability detection in status responses')
    parser.add_argument('--encryption-key', default='unregistered',
                       help='Set custom encryption key for communication (default: unregistered)')
    parser.add_argument('--admin-username', default='admin',
                       help='Admin username for /unitinfo endpoint (default: admin)')
    parser.add_argument('--admin-password', default='me1debug@0567',
                       help='Admin password for /unitinfo endpoint (default: me1debug@0567)')
    
    # Action arguments
    parser.add_argument('--fetch-status', action='store_true', 
                       help='Fetch and display device status')
    parser.add_argument('--detect-capabilities', action='store_true', 
                       help='Detect and display device capabilities')
    parser.add_argument('--enable-echonet', action='store_true', 
                       help='Send ECHONET enable command')
    parser.add_argument('--fetch-unit-info', action='store_true', 
                       help='Fetch unit information from /unitinfo endpoint')
    
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
    api = MitsubishiAPI(
        device_ip=args.device_ip, 
        encryption_key=args.encryption_key,
        admin_username=args.admin_username,
        admin_password=args.admin_password
    )
    controller = MitsubishiController(api=api)
    
    print(f"Mitsubishi Air Conditioner Controller - {args.device_ip}")
    print("=" * 60)
    
    try:
        # Handle capability detection
        if args.detect_capabilities:
            print("🔍 Detecting device capabilities...")
            detector = CapabilityDetector(api=api)
            capabilities = detector.detect_all_capabilities(debug=args.debug)
            
            # Avoid displaying verbose profile analysis unless debug is specified
            if not args.debug:
                capabilities.profile_analysis = None
                
            output = format_output(capabilities.to_dict(), args.format)
            print(output)
            
            # Save capabilities to file
            detector.save_capabilities()
            return 0
        
        # Handle status fetching
        if args.fetch_status:
            print("📊 Fetching device status...")
            success = controller.fetch_status(debug=args.debug, detect_capabilities=args.include_capabilities)
            
            if success:
                print("✅ Successfully fetched device status")
                
                # Get both structured state and summary
                status_data = {
                    'device_state': controller.state.to_dict() if hasattr(controller.state, 'to_dict') else {},
                    'status_summary': controller.get_status_summary()
                }
                
                # Add SwiCago-inspired enhancements summary
                if hasattr(controller.state, 'general') and controller.state.general:
                    general = controller.state.general
                    enhancements = {
                        'swicago_enhancements': {
                            'i_see_sensor_active': general.i_see_sensor,
                            'mode_raw_value': f"0x{general.mode_raw_value:02x}",
                            'wide_vane_adjustment': general.wide_vane_adjustment,
                            'temperature_mode': 'direct' if general.temp_mode else 'segment',
                            'undocumented_patterns_detected': bool(general.undocumented_flags)
                        }
                    }
                    
                    # Enhanced undocumented analysis - examine ALL code entries and profilecodes
                    enhanced_analysis = _analyze_all_undocumented_patterns(api, debug=args.debug)
                    
                    if general.undocumented_flags or enhanced_analysis:
                        # Start with the analysis from general states
                        undoc_analysis = {
                            'general_state_analysis': {
                                'high_bits_count': len(general.undocumented_flags.get('high_bits_set', [])) if general.undocumented_flags else 0,
                                'suspicious_patterns': len(general.undocumented_flags.get('suspicious_patterns', [])) if general.undocumented_flags else 0,
                                'unknown_segments': len(general.undocumented_flags.get('unknown_segments', {})) if general.undocumented_flags else 0
                            }
                        }
                        
                        # Add comprehensive analysis of all codes and profilecodes
                        if enhanced_analysis:
                            undoc_analysis.update(enhanced_analysis)
                        
                        enhancements['undocumented_analysis'] = undoc_analysis
                    
                    status_data.update(enhancements)
                
                # Add energy states if available
                if hasattr(controller.state, 'energy') and controller.state.energy:
                    energy = controller.state.energy
                    energy_summary = {
                        'energy_monitoring': {
                            'compressor_frequency': energy.compressor_frequency,
                            'operating_status': energy.operating,
                            'estimated_power_watts': energy.estimated_power_watts
                        }
                    }
                    status_data.update(energy_summary)
                
                output = format_output(status_data, args.format)
                print("\nDevice Status:")
                print("=" * 20)
                print(output)
            else:
                print("❌ Failed to fetch device status")
                return 1
        
        # Handle unit info fetching
        if args.fetch_unit_info:
            print("🔧 Fetching unit information...")
            unit_info = controller.get_unit_info(debug=args.debug)
            
            if unit_info:
                print("✅ Successfully fetched unit information")
                
                output = format_output(unit_info, args.format)
                print("\nUnit Information:")
                print("=" * 25)
                print(output)
            else:
                print("❌ Failed to fetch unit information")
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
            args.set_power_saving
        ]

        if any(cmd is not None for cmd in control_commands) or args.send_buzzer:
            print("📋 Fetching current device state for control operations...")
            if not controller.fetch_status(debug=args.debug, detect_capabilities=False):
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
        if not any([args.fetch_status, args.detect_capabilities, args.enable_echonet, args.fetch_unit_info, control_executed]):
            print("ℹ️  No specific action requested. Fetching basic status...")
            success = controller.fetch_status(debug=args.debug, detect_capabilities=False)
            
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
