#!/usr/bin/env python3
"""
FC Message Parser and Analyzer

This module parses FC messages from Mitsubishi AC debug logs and analyzes them
using the existing mitsubishi_parser functions.
"""

import re
import sys
from pathlib import Path

# Import the mitsubishi parser functions
sys.path.append(str(Path(__file__).parent.parent / 'pymitsubishi/pymitsubishi/'))

try:
    from mitsubishi_parser import (
        calc_fcc, get_on_off_status, get_drive_mode, parse_mode_with_i_see,
        get_normalized_temperature, PowerOnOff, DriveMode, WindSpeed,
        VerticalWindDirection, HorizontalWindDirection, analyze_undocumented_bits
    )
    MITSUBISHI_PARSER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import mitsubishi_parser: {e}")
    print("Analysis will be limited.")
    MITSUBISHI_PARSER_AVAILABLE = False
    calc_fcc = None
    get_normalized_temperature = lambda x: x

class FCMessageParser:
    def __init__(self, raw_log_line):
        self.raw_line = raw_log_line
        self.timestamp = None
        self.message_type = None
        self.payload_hex = None
        self.payload_bytes = []
        self.analysis = {}
        
    def parse_log_line(self):
        """Parse a full log line to extract FC message components"""
        # Pattern: 2025/08/03_19:08:38 [Ii]FC 62 1 30 10 5 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 58 0 0 0 0
        pattern = r'(\d{4}/\d{2}/\d{2}_\d{2}:\d{2}:\d{2})\s+\[Ii\]FC\s+(.+)'
        match = re.match(pattern, self.raw_line)
        
        if match:
            self.timestamp = match.group(1)
            fc_data = match.group(2).strip()
            self.parse_fc_data(fc_data)
            return True
        return False
    
    def parse_fc_data(self, fc_data):
        """Parse the FC data portion"""
        parts = fc_data.split()
        if len(parts) >= 5:
            # First byte appears to be message type (62 or 42)
            self.message_type = parts[0]
            # Skip some header bytes and get payload
            self.payload_bytes = [int(x, 16) if x != '0' else 0 for x in parts]
            # Convert to hex string for compatibility with existing parser
            self.payload_hex = ''.join([f'{b:02x}' for b in self.payload_bytes])
    
    def analyze_message(self):
        """Analyze the FC message using mitsubishi parser functions"""
        if not self.payload_bytes:
            return {}
            
        analysis = {
            'timestamp': self.timestamp,
            'message_type': self.message_type,
            'payload_length': len(self.payload_bytes),
            'raw_payload': ' '.join([f'{b:02x}' for b in self.payload_bytes]),
        }
        
        # Determine if this is a request (42) or response (62)
        if self.message_type == '42':
            analysis['direction'] = 'request'
        elif self.message_type == '62':
            analysis['direction'] = 'response'
        else:
            analysis['direction'] = 'unknown'
            
        # Try to extract meaningful data from response messages
        if self.message_type == '62' and len(self.payload_bytes) >= 10:
            self.analyze_response_payload(analysis)
            
        # Calculate checksum if possible
        if calc_fcc and len(self.payload_hex) >= 40:
            calculated_checksum = calc_fcc(self.payload_hex[:40])
            analysis['calculated_checksum'] = calculated_checksum
            
        return analysis
    
    def analyze_response_payload(self, analysis):
        """Analyze response payload for AC state information"""
        try:
            # Look for patterns in the payload
            payload = self.payload_bytes
            
            # Skip the first few header bytes and look for data
            if len(payload) > 10:
                # Look for command type in position 4 (0-indexed)
                cmd_type = payload[4] if len(payload) > 4 else 0
                analysis['command_type'] = f'{cmd_type:02x}'
                
                # Analyze based on command type
                if cmd_type == 2:  # Appears to be status data
                    self.analyze_status_data(payload, analysis)
                elif cmd_type == 3:  # Appears to be sensor/temperature data
                    self.analyze_sensor_data(payload, analysis)
                elif cmd_type == 4:  # Unknown data type
                    self.analyze_type4_data(payload, analysis)
                elif cmd_type == 6:  # Another data type
                    self.analyze_type6_data(payload, analysis)
                elif cmd_type == 9:  # Another data type
                    self.analyze_type9_data(payload, analysis)
                    
        except Exception as e:
            analysis['parse_error'] = str(e)
    
    def analyze_status_data(self, payload, analysis):
        """Analyze command type 2 data (appears to be main status)"""
        if len(payload) >= 20:
            # Look for power status
            if payload[7] == 1:  # Position 7 seems to indicate power
                analysis['power'] = 'ON'
            else:
                analysis['power'] = 'OFF'
                
            # Look for mode in position 8
            if len(payload) > 8:
                mode_byte = payload[8]
                analysis['mode_raw'] = f'{mode_byte:02x}'
                
            # Look for fan speed in position 9
            if len(payload) > 9:
                fan_byte = payload[9]
                analysis['fan_raw'] = f'{fan_byte:02x}'
    
    def analyze_sensor_data(self, payload, analysis):
        """Analyze command type 3 data (appears to be sensor/temperature data)"""
        if len(payload) >= 20:
            # This type seems to have temperature and sensor data
            # Look for temperature values in various positions
            temp_candidates = []
            for i in range(10, min(len(payload), 20)):
                if payload[i] > 0x80 and payload[i] < 0xFF:
                    # Could be temperature data
                    temp_val = get_normalized_temperature(payload[i]) if 'get_normalized_temperature' in globals() else payload[i]
                    temp_candidates.append((i, payload[i], temp_val))
            
            if temp_candidates:
                analysis['temperature_candidates'] = temp_candidates
    
    def analyze_type4_data(self, payload, analysis):
        """Analyze command type 4 data"""
        if len(payload) >= 10:
            # Look for the 0x80 value that appears frequently
            if payload[8] == 0x80:
                analysis['type4_flag'] = 'sensor_data_present'
    
    def analyze_type6_data(self, payload, analysis):
        """Analyze command type 6 data"""
        if len(payload) >= 15:
            # This type seems to have various sensor readings
            analysis['type6_data'] = {
                'byte_10': f'{payload[10]:02x}',
                'byte_11': f'{payload[11]:02x}',
                'byte_12': f'{payload[12]:02x}',
            }
    
    def analyze_type9_data(self, payload, analysis):
        """Analyze command type 9 data"""
        if len(payload) >= 10:
            # This type often has a 1 in position 8
            if payload[8] == 1:
                analysis['type9_flag'] = 'active'

def parse_fc_logs(log_content):
    """Parse multiple FC messages from log content"""
    results = []
    lines = log_content.split('\n')
    
    for line in lines:
        if '[Ii]FC' in line:
            parser = FCMessageParser(line)
            if parser.parse_log_line():
                analysis = parser.analyze_message()
                results.append(analysis)
    
    return results

def analyze_patterns(results):
    """Analyze patterns across multiple FC messages"""
    patterns = {
        'message_types': {},
        'command_types': {},
        'request_response_pairs': [],
        'timing_patterns': []
    }
    
    for result in results:
        # Count message types
        msg_type = result.get('message_type', 'unknown')
        patterns['message_types'][msg_type] = patterns['message_types'].get(msg_type, 0) + 1
        
        # Count command types
        cmd_type = result.get('command_type', 'unknown')
        patterns['command_types'][cmd_type] = patterns['command_types'].get(cmd_type, 0) + 1
    
    return patterns

if __name__ == '__main__':
    # Sample FC messages from the logs
    sample_logs = [
        "2025/08/03_19:08:38 [Ii]FC 62 1 30 10 5 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 58 0 0 0 0",
        "2025/08/03_19:08:39 [Ii]FC 42 1 30 10 3 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0",
        "2025/08/03_19:08:39 [Ii]FC 62 1 30 10 3 0 0 D 0 AC AE AE FE 42 0 11 C1 A4 0 0 8F 0 0 0 0",
        "2025/08/03_19:08:40 [Ii]FC 62 1 30 10 4 0 0 0 80 0 0 0 0 0 0 0 0 0 0 0 D9 0 0 0 0",
        "2025/08/03_19:08:41 [Ii]FC 62 1 30 10 2 0 0 1 3 7 0 1 0 0 85 B0 28 0 0 0 F2 0 0 0 0",
    ]
    
    print("FC Message Analysis:")
    print("=" * 50)
    
    all_results = []
    for log_line in sample_logs:
        parser = FCMessageParser(log_line)
        if parser.parse_log_line():
            analysis = parser.analyze_message()
            all_results.append(analysis)
            
            print(f"\nTimestamp: {analysis['timestamp']}")
            print(f"Type: {analysis['message_type']} ({analysis['direction']})")
            print(f"Command: {analysis.get('command_type', 'N/A')}")
            print(f"Payload: {analysis['raw_payload']}")
            
            if 'power' in analysis:
                print(f"Power: {analysis['power']}")
            if 'mode_raw' in analysis:
                print(f"Mode: {analysis['mode_raw']}")
            if 'temperature_candidates' in analysis:
                print(f"Temperature candidates: {analysis['temperature_candidates']}")
    
    # Analyze patterns
    patterns = analyze_patterns(all_results)
    print("\n\nPattern Analysis:")
    print("=" * 50)
    print(f"Message types: {patterns['message_types']}")
    print(f"Command types: {patterns['command_types']}")
