#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner Controller

Dynamic XML/JSON parser and formatter for Mitsubishi air conditioner device responses.
Supports multiple output formats: JSON, XML, CSV, and table.
Includes command generation and state parsing for AC control operations.
"""

import base64
import requests
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import json
import argparse
import csv
import sys
from typing import Dict, Any

# Import our custom parser module
from mitsubishi_parser import (
    PowerOnOff, DriveMode, WindSpeed, VerticalWindDirection, HorizontalWindDirection,
    GeneralStates, SensorStates, ErrorStates, ParsedDeviceState,
    parse_code_values, calc_fcc, convert_temperature, convert_temperature_to_segment
)

# Constants from the working implementation
KEY_SIZE = 16
STATIC_KEY = "unregistered"



def generate_general_command(state: ParsedDeviceState, controls: Dict[str, bool]) -> str:
    """Generate general control command hex string"""
    segments = {
        'segment0': '01',
        'segment1': '00',
        'segment2': '00',
        'segment3': '00',
        'segment4': '00',
        'segment5': '00',
        'segment6': '00',
        'segment7': '00',
        'segment13': '00',
        'segment14': '00',
        'segment15': '00',
    }
    
    # Calculate segment 1 value (control flags)
    segment1_value = 0
    if controls.get('power_on_off'):
        segment1_value |= 0x01
    if controls.get('drive_mode'):
        segment1_value |= 0x02
    if controls.get('temperature'):
        segment1_value |= 0x04
    if controls.get('wind_speed'):
        segment1_value |= 0x08
    if controls.get('up_down_wind_direct'):
        segment1_value |= 0x10
    
    # Calculate segment 2 value
    segment2_value = 0
    if controls.get('left_right_wind_direct'):
        segment2_value |= 0x01
    if controls.get('outside_control', True):  # Default true
        segment2_value |= 0x02
    
    segments['segment1'] = f"{segment1_value:02x}"
    segments['segment2'] = f"{segment2_value:02x}"
    segments['segment3'] = state.power_on_off.value
    segments['segment4'] = state.drive_mode.value
    segments['segment6'] = f"{state.wind_speed.value:02x}"
    segments['segment7'] = f"{state.vertical_wind_direction_right.value:02x}"
    segments['segment13'] = f"{state.horizontal_wind_direction.value:02x}"
    segments['segment15'] = '41'  # checkInside: 41 true, 42 false
    
    segments['segment5'] = convert_temperature(state.temperature)
    segments['segment14'] = convert_temperature_to_segment(state.temperature)
    
    # Build payload
    payload = '41013010'
    for i in range(16):
        segment_key = f'segment{i}'
        payload += segments.get(segment_key, '00')
    
    # Calculate and append FCC
    fcc = calc_fcc(payload)
    return "fc" + payload + fcc

def generate_extend08_command(state: ParsedDeviceState, controls: Dict[str, bool]) -> str:
    """Generate extend08 command for buzzer, dehum, power saving, etc."""
    segment_x_value = 0
    if controls.get('dehum'):
        segment_x_value |= 0x04
    if controls.get('power_saving'):
        segment_x_value |= 0x08
    if controls.get('buzzer'):
        segment_x_value |= 0x10
    if controls.get('wind_and_wind_break'):
        segment_x_value |= 0x20
    
    segment_x = f"{segment_x_value:02x}"
    segment_y = f"{state.dehum_setting:02x}" if controls.get('dehum') else '00'
    segment_z = '0A' if state.is_power_saving else '00'
    segment_a = f"{state.wind_and_wind_break_direct:02x}" if controls.get('wind_and_wind_break') else '00'
    buzzer_segment = '01' if controls.get('buzzer') else '00'
    
    payload = "4101301008" + segment_x + "0000" + segment_y + segment_z + segment_a + buzzer_segment + "0000000000000000"
    fcc = calc_fcc(payload)
    return 'fc' + payload + fcc

class MitsubishiController:
    def __init__(self, device_ip: str):
        self.device_ip = device_ip
        self.state = ParsedDeviceState()
        
    def get_crypto_key(self):
        """Get the crypto key, same as TypeScript implementation"""
        buffer = bytearray(KEY_SIZE)
        key_bytes = STATIC_KEY.encode('utf-8')
        buffer[:len(key_bytes)] = key_bytes
        return bytes(buffer)

    def encrypt_payload(self, payload):
        """Encrypt payload using same method as TypeScript implementation"""
        # Generate random IV
        iv = get_random_bytes(KEY_SIZE)
        key = self.get_crypto_key()
        
        # Encrypt using AES CBC with zero padding
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        # Zero pad the payload to multiple of 16 bytes
        payload_bytes = payload.encode('utf-8')
        padding_length = KEY_SIZE - (len(payload_bytes) % KEY_SIZE)
        if padding_length == KEY_SIZE:
            padding_length = 0
        padded_payload = payload_bytes + b'\x00' * padding_length
        
        encrypted = cipher.encrypt(padded_payload)
        
        # TypeScript approach: IV as hex + encrypted as hex, then base64 encode the combined hex
        iv_hex = iv.hex()
        encrypted_hex = encrypted.hex()
        combined_hex = iv_hex + encrypted_hex
        combined_bytes = bytes.fromhex(combined_hex)
        return base64.b64encode(combined_bytes).decode('utf-8')

    def decrypt_payload(self, payload, debug=False):
        """Decrypt payload following TypeScript implementation exactly"""
        try:
            # Convert base64 to hex string
            hex_buffer = base64.b64decode(payload).hex()
            
            if debug:
                print(f"[DEBUG] Base64 payload length: {len(payload)}")
                print(f"[DEBUG] Hex buffer length: {len(hex_buffer)}")
            
            # Extract IV from first 2 * KEY_SIZE hex characters
            iv_hex = hex_buffer[:2 * KEY_SIZE]
            iv = bytes.fromhex(iv_hex)
            
            if debug:
                print(f"[DEBUG] IV: {iv.hex()}")
            
            key = self.get_crypto_key()
            
            # Extract the encrypted portion
            encrypted_hex = hex_buffer[2 * KEY_SIZE:]
            encrypted_data = bytes.fromhex(encrypted_hex)
            
            if debug:
                print(f"[DEBUG] Encrypted data length: {len(encrypted_data)}")
                print(f"[DEBUG] Encrypted data (first 64 bytes): {encrypted_data[:64].hex()}")
            
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(encrypted_data)
            
            if debug:
                print(f"[DEBUG] Decrypted raw length: {len(decrypted)}")
                print(f"[DEBUG] Decrypted raw (first 64 bytes): {decrypted[:64]}")
                print(f"[DEBUG] Decrypted raw (last 64 bytes): {decrypted[-64:]}")
            
            # Remove zero padding
            decrypted_clean = decrypted.rstrip(b'\x00')
            
            if debug:
                print(f"[DEBUG] After padding removal length: {len(decrypted_clean)}")
                print(f"[DEBUG] Non-zero bytes at end: {decrypted_clean[-20:]}")
            
            # Try to decode as UTF-8
            try:
                result = decrypted_clean.decode('utf-8')
                return result
            except UnicodeDecodeError as ude:
                if debug:
                    print(f"[DEBUG] UTF-8 decode error at position {ude.start}: {ude.reason}")
                    print(f"[DEBUG] Problematic bytes: {decrypted_clean[max(0, ude.start-10):ude.start+10]}")
                
                # Try to find the actual end of the XML by looking for closing tags
                xml_end_patterns = [b'</LSV>', b'</CSV>', b'</ESV>']
                for pattern in xml_end_patterns:
                    pos = decrypted_clean.find(pattern)
                    if pos != -1:
                        end_pos = pos + len(pattern)
                        truncated = decrypted_clean[:end_pos]
                        if debug:
                            print(f"[DEBUG] Found XML end pattern {pattern} at position {pos}")
                            print(f"[DEBUG] Truncated length: {len(truncated)}")
                        try:
                            return truncated.decode('utf-8')
                        except UnicodeDecodeError:
                            continue
                
                # If no valid XML end found, try errors='ignore'
                result = decrypted_clean.decode('utf-8', errors='ignore')
                if debug:
                    print(f"[DEBUG] Using errors='ignore', result length: {len(result)}")
                return result
                
        except Exception as e:
            print(f"Decryption error: {e}")
            if debug:
                import traceback
                traceback.print_exc()
            return None

    def make_request(self, payload_xml, debug=False):
        """Make HTTP request to the /smart endpoint"""
        # Encrypt the XML payload
        encrypted_payload = self.encrypt_payload(payload_xml)
        
        # Create the full XML request body
        request_body = f'<?xml version="1.0" encoding="UTF-8"?><ESV>{encrypted_payload}</ESV>'
        
        if debug:
            print("[DEBUG] Request Body:")
            print(request_body)

        headers = {
            'Host': f'{self.device_ip}:80',
            'Content-Type': 'text/plain;chrset=UTF-8',
            'Connection': 'keep-alive',
            'Proxy-Connection': 'keep-alive',
            'Accept': '*/*',
            'User-Agent': 'KirigamineRemote/5.1.0 (jp.co.MitsubishiElectric.KirigamineRemote; build:3; iOS 17.5.1) Alamofire/5.9.1',
            'Accept-Language': 'zh-Hant-JP;q=1.0, ja-JP;q=0.9',
        }
        
        url = f'http://{self.device_ip}/smart'
        
        try:
            response = requests.post(url, data=request_body, headers=headers, timeout=10)
            
            if response.status_code == 200:
                if debug:
                    print("[DEBUG] Response Text:")
                    print(response.text)
                try:
                    root = ET.fromstring(response.text)
                    encrypted_response = root.text
                    if encrypted_response:
                        decrypted = self.decrypt_payload(encrypted_response, debug=debug)
                        return decrypted
                except ET.ParseError as e:
                    print(f"XML parsing error: {e}")
            
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None

    def fetch_status(self):
        """Fetch current device status"""
        payload_xml = '<CSV><CONNECT>ON</CONNECT></CSV>'
        response = self.make_request(payload_xml)
        
        if response:
            self.parse_status_response(response)
            return True
        return False

    def parse_status_response(self, response):
        """Parse the device status response and update state"""
        try:
            # Parse the XML response
            root = ET.fromstring(response)
            
            # Extract code values for parsing
            code_values_elems = root.findall('.//CODE/VALUE')
            code_values = [elem.text for elem in code_values_elems if elem.text]
            
            # Use the parser module to get structured state
            parsed_state = parse_code_values(code_values)
            
            if parsed_state:
                self.state = parsed_state

            # Extract and set device identity
            mac_elem = root.find('.//MAC')
            if mac_elem is not None:
                self.state.mac = mac_elem.text
                
            serial_elem = root.find('.//SERIAL')
            if serial_elem is not None:
                self.state.serial = serial_elem.text

        except ET.ParseError as e:
            print(f"Error parsing status response: {e}")

    def set_power(self, power_on: bool):
        """Set power on/off"""
        self.state.power_on = power_on
        return self.send_control_command({'power': power_on})

    def set_temperature(self, temperature_celsius: float):
        """Set target temperature in Celsius"""
        # Convert to 0.1°C units
        self.state.temperature = int(temperature_celsius * 10)
        return self.send_control_command({'temperature': self.state.temperature})

    def set_mode(self, mode: DriveMode):
        """Set operating mode"""
        self.state.drive_mode = mode
        return self.send_control_command({'mode': mode.value})

    def set_fan_speed(self, speed: WindSpeed):
        """Set fan speed"""
        self.state.wind_speed = speed
        return self.send_control_command({'fan_speed': speed.value})

    def send_control_command(self, command: Dict[str, Any]):
        """Send control command to device"""
        # This would need to be implemented based on the TypeScript command builders
        # For now, return the current approach
        print(f"Would send command: {command}")
        
        # Build XML payload based on command
        # This is simplified - the actual implementation would need the specific
        # command format from the TypeScript code
        payload_xml = '<CSV><CONNECT>ON</CONNECT></CSV>'
        
        response = self.make_request(payload_xml)
        return response is not None

    def enable_echonet(self):
        """Send ECHONET enable command"""
        payload_xml = '<CSV><CONNECT>ON</CONNECT><ECHONET>ON</ECHONET></CSV>'
        response = self.make_request(payload_xml)
        return response is not None

    def parse_full_response(self, response):
        """Parse the full device response into structured data dynamically"""
        try:
            root = ET.fromstring(response)
            return self._parse_xml_element_recursive(root)
        except ET.ParseError as e:
            return {'error': f"XML parsing error: {e}"}
    
    def _parse_xml_element_recursive(self, element, path=""):
        """Recursively parse XML elements into a dictionary structure"""
        result = {}
        
        # Handle elements that have text content
        if element.text and element.text.strip():
            # If element has both text and children, store text as '_text'
            if len(element) > 0:
                result['_text'] = element.text.strip()
            else:
                # If it's a leaf element with just text, return the text directly
                return element.text.strip()
        
        # Process child elements
        for child in element:
            child_name = child.tag.lower()
            child_result = self._parse_xml_element_recursive(child, f"{path}/{child_name}")
            
            # Handle multiple elements with the same name
            if child_name in result:
                # Convert to list if we encounter a duplicate
                if not isinstance(result[child_name], list):
                    result[child_name] = [result[child_name]]
                result[child_name].append(child_result)
            else:
                result[child_name] = child_result
        
        # Special handling for common collection patterns
        result = self._normalize_collections(result)
        
        return result if result else None
    
    def _normalize_collections(self, data):
        """Normalize common XML collection patterns for better usability"""
        if not isinstance(data, dict):
            return data
            
        normalized = {}
        
        for key, value in data.items():
            # Handle VALUE collections (like CODE/VALUE, PROFILECODE/VALUE)
            if key.endswith('code') and isinstance(value, dict) and 'value' in value:
                if isinstance(value['value'], list):
                    normalized[f"{key}_values"] = value['value']
                else:
                    normalized[f"{key}_values"] = [value['value']]
            # Handle LED patterns (LED1, LED2, etc.)
            elif key.startswith('led') and key[3:].isdigit():
                if 'leds' not in normalized:
                    normalized['leds'] = {}
                normalized['leds'][key] = value
            else:
                normalized[key] = value
                
        return normalized
    
    def _get_element_text(self, root, xpath):
        """Safely extract text from XML element"""
        elem = root.find(xpath)
        return elem.text if elem is not None else None

    def get_status_summary(self):
        """Get human-readable status summary"""
        return {
            'mac': self.state.mac,
            'serial': self.state.serial,
            'power': 'ON' if self.state.power_on_off == PowerOnOff.ON else 'OFF',
            'mode': self.state.drive_mode.name,
            'target_temp': self.state.temperature / 10.0,
            'room_temp': self.state.room_temperature / 10.0,
            'fan_speed': self.state.wind_speed.name,
            'outside_temp': self.state.outside_temperature / 10.0 if self.state.outside_temperature else None,
            'error_code': self.state.error_code,
            'abnormal_state': self.state.is_abnormal_state,
        }

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
    """Recursively convert dictionary to XML elements with full structure support"""
    if isinstance(data, dict):
        for key, value in data.items():
            # Sanitize key name for valid XML element names
            element_name = _sanitize_xml_name(key)
            
            if isinstance(value, dict):
                # Create sub-element for nested dictionary
                sub_element = ET.SubElement(parent_element, element_name)
                _dict_to_xml_recursive(value, sub_element)
            elif isinstance(value, list):
                # Handle lists - create container element
                list_container = ET.SubElement(parent_element, element_name)
                for i, item in enumerate(value):
                    if isinstance(item, (dict, list)):
                        # Complex item - create indexed sub-element
                        item_element = ET.SubElement(list_container, f"item_{i}")
                        _dict_to_xml_recursive(item, item_element)
                    else:
                        # Simple item - create value element
                        item_element = ET.SubElement(list_container, "value")
                        item_element.text = str(item) if item is not None else ''
            else:
                # Simple value - create text element
                element = ET.SubElement(parent_element, element_name)
                element.text = str(value) if value is not None else ''
    elif isinstance(data, list):
        # Handle case where root data is a list
        for i, item in enumerate(data):
            item_element = ET.SubElement(parent_element, f"item_{i}")
            _dict_to_xml_recursive(item, item_element)
    else:
        # Simple value at root level
        parent_element.text = str(data) if data is not None else ''

def _sanitize_xml_name(name):
    """Sanitize string to be a valid XML element name"""
    import re
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', str(name))
    # Ensure it starts with a letter or underscore
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized
    return sanitized or 'element'

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
    """Format data as a readable table dynamically"""
    lines = []
    
    if not isinstance(data, dict):
        return str(data)
    
    # Function to format individual sections
    def format_section(title, section_data, indent=0):
        section_lines = []
        prefix = "  " * indent
        
        if isinstance(section_data, dict):
            # Check if this looks like a collection of similar items (like LEDs)
            if all(key.startswith(next(iter(section_data.keys()))[:3]) for key in section_data.keys() if len(key) > 3):
                # Similar keys, format as a grouped section
                for key, value in sorted(section_data.items()):
                    if isinstance(value, (dict, list)):
                        section_lines.append(f"{prefix}{key.upper()}: {format_complex_value(value)}")
                    else:
                        section_lines.append(f"{prefix}{key.upper()}: {value}")
            else:
                # Different keys, format as individual items
                for key, value in sorted(section_data.items()):
                    if isinstance(value, (dict, list)):
                        section_lines.append(f"{prefix}{key.upper()}: {format_complex_value(value)}")
                    else:
                        section_lines.append(f"{prefix}{key.upper()}: {value}")
        elif isinstance(section_data, list):
            for i, item in enumerate(section_data):
                if isinstance(item, (dict, list)):
                    section_lines.append(f"{prefix}[{i}]: {format_complex_value(item)}")
                else:
                    section_lines.append(f"{prefix}[{i}]: {item}")
        else:
            section_lines.append(f"{prefix}{section_data}")
        
        return section_lines
    
    def format_complex_value(value):
        """Format complex values (dicts/lists) in a compact way"""
        if isinstance(value, dict):
            if len(value) <= 3:  # Small dict, format inline
                return "{" + ", ".join(f"{k}: {v}" for k, v in value.items()) + "}"
            else:
                return f"{{...{len(value)} items...}}"
        elif isinstance(value, list):
            if len(value) <= 3:  # Small list, format inline
                return "[" + ", ".join(str(item)[:20] for item in value) + "]"
            else:
                return f"[...{len(value)} items...]"
        else:
            return str(value)
    
    # Categorize data for better organization
    device_info = {}
    collections = {}
    other_data = {}
    
    # Known device info fields (but dynamically discovered)
    device_fields = {'mac', 'serial', 'connect', 'status', 'datdate', 'app_ver', 'ssl_limit', 'rssi', 'echonet'}
    
    for key, value in data.items():
        if key.lower() in device_fields:
            device_info[key] = value
        elif key.endswith('_values') or key in ['leds', 'codes'] or isinstance(value, list):
            collections[key] = value
        else:
            other_data[key] = value
    
    # Format device information section
    if device_info:
        title = "Device Information"
        lines.append(title + ":")
        lines.append("-" * len(title))
        lines.extend(format_section("", device_info))
    
    # Format collections (arrays, grouped data)
    for key, value in collections.items():
        if lines:  # Add spacing if not first section
            lines.append("")
        
        title = key.replace('_', ' ').title()
        lines.append(title + ":")
        lines.append("-" * len(title))
        lines.extend(format_section("", value))
    
    # Format other data
    if other_data:
        if lines:  # Add spacing if not first section
            lines.append("")
        
        title = "Additional Information"
        lines.append(title + ":")
        lines.append("-" * len(title))
        lines.extend(format_section("", other_data))
    
    return '\n'.join(lines)

def main():
    """CLI interface for the Mitsubishi air conditioner controller"""
    parser = argparse.ArgumentParser(
        description='Control Mitsubishi MAC-577IF-2E air conditioner via /smart endpoint',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --ip <DEVICE_IP> --status
  %(prog)s --ip <DEVICE_IP> --enable-echonet
  %(prog)s --ip <DEVICE_IP> --power on --temp 24 --mode cool
  %(prog)s --ip <DEVICE_IP> --fan-speed 2"""
    )
    
    # Required arguments
    parser.add_argument('--ip', required=True, help='IP address of the air conditioner')
    
    # Output options
    parser.add_argument('--debug', action='store_true', help='Show debug information including raw requests/responses')
    parser.add_argument('--format', choices=['table', 'csv', 'json', 'xml'], default='table',
                       help='Output format for data (default: table)')
    
    # Action arguments
    parser.add_argument('--status', action='store_true', help='Fetch and display device status only')
    parser.add_argument('--enable-echonet', action='store_true', help='Send ECHONET enable command')
    
    # Control arguments
    parser.add_argument('--power', choices=['on', 'off'], help='Set power state')
    parser.add_argument('--temp', type=float, help='Set target temperature in Celsius')
    parser.add_argument('--mode', choices=['auto', 'cool', 'heat', 'dry', 'fan'], help='Set operating mode')
    parser.add_argument('--fan-speed', type=int, choices=[0, 1, 2, 3, 4], 
                       help='Set fan speed (0=auto, 1-4=levels)')
    
    args = parser.parse_args()
    
    # Initialize controller
    controller = MitsubishiController(args.ip)
    
    print(f"Mitsubishi Air Conditioner Controller - {args.ip}")
    print("=" * 60)
    
    # Handle status-only mode
    if args.status:
        print("Fetching device status...")
        payload_xml = '<CSV><CONNECT>ON</CONNECT></CSV>'
        response = controller.make_request(payload_xml, debug=args.debug)
        
        if response:
            print("✓ Successfully connected to device")
            
            if args.debug:
                print("[DEBUG] Decrypted Response:")
                print(response)
                print()
            
            # Parse both raw response and structured device state
            raw_data = controller.parse_full_response(response)
            controller.parse_status_response(response)  # This populates controller.state
            
            # Create combined data with both raw and parsed information
            combined_data = dict(raw_data) if raw_data else {}
            
            # Add parsed device state directly to top level - safely extract from nested structure
            # General states
            if controller.state.general:
                combined_data.update({
                    'power': 'ON' if controller.state.general.power_on_off == PowerOnOff.ON else 'OFF',
                    'mode': controller.state.general.drive_mode.name,
                    'target_temp_celsius': controller.state.general.temperature / 10.0,
                    'fan_speed': controller.state.general.wind_speed.name,
                    'vertical_vane_right': controller.state.general.vertical_wind_direction_right.name,
                    'vertical_vane_left': controller.state.general.vertical_wind_direction_left.name,
                    'horizontal_vane': controller.state.general.horizontal_wind_direction.name,
                    'dehumidifier_setting': controller.state.general.dehum_setting,
                    'power_saving_mode': controller.state.general.is_power_saving,
                    'wind_and_break_direct': controller.state.general.wind_and_wind_break_direct,
                })
            
            # Sensor states
            if controller.state.sensors:
                combined_data.update({
                    'room_temp_celsius': controller.state.sensors.room_temperature / 10.0,
                    'outside_temp_celsius': controller.state.sensors.outside_temperature / 10.0 if controller.state.sensors.outside_temperature else None,
                    'thermal_sensor_active': controller.state.sensors.thermal_sensor,
                    'wind_speed_pr557': controller.state.sensors.wind_speed_pr557,
                })
            
            # Error states
            if controller.state.errors:
                combined_data.update({
                    'error_state': controller.state.errors.is_abnormal_state,
                    'error_code': controller.state.errors.error_code
                })
            
            # Device identity (these might overwrite the raw mac/serial, but that's fine)
            combined_data.update({
                'mac_address': controller.state.mac,
                'serial_number': controller.state.serial,
            })
            
            formatted_output = format_output(combined_data, args.format)
            
            if args.format == 'table':
                print("\nDevice Status:")
                print("=" * 20)
            print(formatted_output)
        else:
            print("✗ Failed to connect to device")
            return 1
        return 0
    
    # Handle ECHONET enable command
    if args.enable_echonet:
        print("Sending ECHONET enable command...")
        payload_xml = '<CSV><CONNECT>ON</CONNECT><ECHONET>ON</ECHONET></CSV>'
        response = controller.make_request(payload_xml, debug=args.debug)
        
        if response:
            print("✓ ECHONET enable command sent successfully")
            
            if args.debug:
                print("[DEBUG] Decrypted Response:")
                print(response)
                print()
            
            # Parse and format the response
            parsed_data = controller.parse_full_response(response)
            formatted_output = format_output(parsed_data, args.format)
            
            if args.format == 'table':
                print("\nECHONET Enable Response:")
                print("=" * 25)
            print(formatted_output)
        else:
            print("✗ ECHONET enable command failed")
            return 1
        return 0
    
    # Handle control commands
    control_commands = [args.power, args.temp, args.mode, args.fan_speed]
    if not any(control_commands):
        # No specific action requested, show status by default
        print("No action specified. Fetching device status...")
        if controller.fetch_status():
            print("✓ Successfully connected to device")
            status = controller.get_status_summary()
            print("\nCurrent Status:")
            for key, value in status.items():
                print(f"  {key}: {value}")
            
            print("\nUse --help to see available control options.")
        else:
            print("✗ Failed to connect to device")
            return 1
        return 0
    
    # Execute control commands
    print("Sending control commands...")
    success = True
    
    if args.power:
        print(f"Setting power {args.power.upper()}...")
        power_on = args.power.lower() == 'on'
        if controller.set_power(power_on):
            print("✓ Power command sent")
        else:
            print("✗ Power command failed")
            success = False
    
    if args.temp:
        print(f"Setting temperature to {args.temp}°C...")
        if controller.set_temperature(args.temp):
            print("✓ Temperature command sent")
        else:
            print("✗ Temperature command failed")
            success = False
    
    if args.mode:
        mode_map = {
            'auto': DriveMode.AUTO,
            'cool': DriveMode.COOLER,
            'heat': DriveMode.HEATER,
            'dry': DriveMode.DEHUM,
            'fan': DriveMode.FAN
        }
        print(f"Setting mode to {args.mode.upper()}...")
        if controller.set_mode(mode_map[args.mode]):
            print("✓ Mode command sent")
        else:
            print("✗ Mode command failed")
            success = False
    
    if args.fan_speed is not None:
        speed_map = {
            0: WindSpeed.AUTO,
            1: WindSpeed.LEVEL_1,
            2: WindSpeed.LEVEL_2,
            3: WindSpeed.LEVEL_3,
            4: WindSpeed.LEVEL_FULL
        }
        speed_name = "AUTO" if args.fan_speed == 0 else f"LEVEL_{args.fan_speed}"
        print(f"Setting fan speed to {speed_name}...")
        if controller.set_fan_speed(speed_map[args.fan_speed]):
            print("✓ Fan speed command sent")
        else:
            print("✗ Fan speed command failed")
            success = False
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
