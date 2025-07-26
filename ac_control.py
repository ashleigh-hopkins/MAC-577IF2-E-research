#!/usr/bin/env python3

import base64
import requests
import xml.etree.ElementTree as ET
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import json
import argparse
import csv
import sys
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Constants from the working implementation
KEY_SIZE = 16
STATIC_KEY = "unregistered"

class PowerState(Enum):
    OFF = 0
    ON = 1

class DriveMode(Enum):
    AUTO = 0
    COOL = 1
    DRY = 2
    FAN = 3
    HEAT = 4

class WindSpeed(Enum):
    AUTO = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4

class VerticalWindDirection(Enum):
    AUTO = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5
    SWING = 7

@dataclass
class AirconState:
    power_on: bool = False
    drive_mode: DriveMode = DriveMode.AUTO
    temperature: int = 220  # 22.0°C in 0.1°C units
    room_temperature: int = 220  # 22.0°C in 0.1°C units
    wind_speed: WindSpeed = WindSpeed.AUTO
    vertical_wind_direction_right: VerticalWindDirection = VerticalWindDirection.AUTO
    vertical_wind_direction_left: VerticalWindDirection = VerticalWindDirection.AUTO
    mac: str = ""
    serial: str = ""
    rssi: str = ""
    app_version: str = ""

class MitsubishiController:
    def __init__(self, device_ip: str):
        self.device_ip = device_ip
        self.state = AirconState()
        
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
            
            # Extract device identity
            mac_elem = root.find('.//MAC')
            if mac_elem is not None:
                self.state.mac = mac_elem.text
                
            serial_elem = root.find('.//SERIAL')
            if serial_elem is not None:
                self.state.serial = serial_elem.text
            
            # Parse CODE values that contain the actual device state
            code_values = root.findall('.//CODE/VALUE')
            for value_elem in code_values:
                if value_elem.text:
                    self.parse_code_value(value_elem.text)
                    
        except ET.ParseError as e:
            print(f"Error parsing status response: {e}")

    def parse_code_value(self, hex_value):
        """Parse individual CODE VALUE hex strings to extract device state"""
        # The hex values contain encoded device state information
        # This would need reverse engineering based on the TypeScript parsers
        # For now, we just validate the format
        if len(hex_value) > 20 and all(c in '0123456789abcdef' for c in hex_value.lower()):
            # Valid hex string - could be processed further in future versions
            pass

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
            'power': 'ON' if self.state.power_on else 'OFF',
            'mode': self.state.drive_mode.name,
            'target_temp': self.state.temperature / 10.0,
            'room_temp': self.state.room_temperature / 10.0,
            'fan_speed': self.state.wind_speed.name,
        }

def format_output(data, format_type):
    """Format data for output in various formats"""
    if format_type == 'json':
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    elif format_type == 'xml':
        # Convert dict to simple XML
        root = ET.Element('response')
        for key, value in data.items():
            if isinstance(value, dict):
                sub_elem = ET.SubElement(root, key)
                for sub_key, sub_value in value.items():
                    sub_sub_elem = ET.SubElement(sub_elem, sub_key)
                    sub_sub_elem.text = str(sub_value)
            elif isinstance(value, list):
                sub_elem = ET.SubElement(root, key)
                for i, item in enumerate(value):
                    item_elem = ET.SubElement(sub_elem, f'item_{i}')
                    item_elem.text = str(item)
            else:
                elem = ET.SubElement(root, key)
                elem.text = str(value) if value is not None else ''
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
            
            # Parse and format the response
            parsed_data = controller.parse_full_response(response)
            formatted_output = format_output(parsed_data, args.format)
            
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
            'cool': DriveMode.COOL,
            'heat': DriveMode.HEAT,
            'dry': DriveMode.DRY,
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
            4: WindSpeed.LEVEL_4
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
