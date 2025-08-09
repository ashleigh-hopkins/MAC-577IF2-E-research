#!/usr/bin/env python3
"""
MAC-577IF2-E Firmware Dumper

A streamlined CLI tool for extracting firmware from Mitsubishi MAC-577IF2-E WiFi adapters.
Based on research from: https://github.com/ncaunt/meldec/issues/2

Features:
- Non-interactive CLI interface
- Built-in admin credentials (no password prompts)
- Configurable dump parameters (offset, size, commands)
- Real-time progress reporting during dumps
- Automatic retry/recovery logic for unstable devices
- Resume capability for interrupted dumps
"""

import requests
import socket
import time
import sys
import os
import json
import argparse
import re
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin
from datetime import datetime

class MAC577IF2EDumper:
    def __init__(self, device_ip, admin_password=None):
        self.device_ip = device_ip
        self.base_url = f"http://{device_ip}"
        
        # Use built-in admin credentials (discovered from research)
        self.admin_username = "admin"
        self.admin_password = admin_password or "me1debug@0567"
        
        self.session = requests.Session()
        self.telnet_socket = None
        
    def log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def check_device_access(self):
        """Verify we can access the device admin interface"""
        try:
            self.log(f"Testing admin access to {self.device_ip}...")
            response = self.session.get(
                urljoin(self.base_url, "/analyze"),
                auth=HTTPBasicAuth(self.admin_username, self.admin_password),
                timeout=10
            )
            if response.status_code == 200:
                self.log("Admin access confirmed")
                return True
            else:
                self.log(f"Admin access failed (status {response.status_code})", "ERROR")
                return False
        except Exception as e:
            self.log(f"Failed to connect to device: {e}", "ERROR")
            return False
    
    def get_analyze_status(self):
        """Get current analyze mode status"""
        try:
            response = self.session.get(
                urljoin(self.base_url, "/analyze"),
                auth=HTTPBasicAuth(self.admin_username, self.admin_password),
                timeout=10
            )
            
            if response.status_code == 200:
                content = response.text
                if 'value="ON" Selected' in content:
                    return "ON"
                elif 'value="OFF" Selected' in content:
                    return "OFF"
            return None
        except Exception as e:
            self.log(f"Error checking analyze status: {e}", "ERROR")
            return None
    
    def enable_analyze_mode(self, force_toggle=False):
        """Enable analyze/debug mode to activate telnet"""
        self.log("Enabling analyze mode...")
        
        try:
            current_status = self.get_analyze_status()
            self.log(f"Current analyze status: {current_status}")
            
            if current_status == "ON" and not force_toggle:
                self.log("Analyze mode already enabled")
                return True
            
            # Only toggle if not ON or if force_toggle is true
            if current_status != "ON" or force_toggle:
                # Disable first to reset the mode if necessary
                if current_status == "ON" or force_toggle:
                    self.log("Disabling analyze mode first to reset...")
                    disable_data = {'debugStatus': 'OFF'}
                    
                    try:
                        response = self.session.post(
                            urljoin(self.base_url, "/analyze"),
                            auth=HTTPBasicAuth(self.admin_username, self.admin_password),
                            data=disable_data,
                            timeout=30
                        )
                        
                        if response.status_code not in [200, 301, 302]:
                            self.log(f"Warning: Failed to disable analyze mode: {response.status_code}")
                        else:
                            self.log("Analyze mode disabled")
                    except Exception as disable_error:
                        self.log(f"Warning: Exception disabling analyze mode: {disable_error}")
                    
                    # Wait for device to settle
                    self.log("Waiting for device to settle...")
                    time.sleep(5)
            
            # Enable analyze mode
            self.log("Enabling analyze mode...")
            enable_data = {'debugStatus': 'ON'}
            response = self.session.post(
                urljoin(self.base_url, "/analyze"),
                auth=HTTPBasicAuth(self.admin_username, self.admin_password),
                data=enable_data,
                timeout=30
            )
            
            if response.status_code in [200, 301, 302]:
                self.log("Analyze mode enabled successfully")
                time.sleep(5)  # Wait for telnet to become available
                return True
            else:
                self.log(f"Failed to enable analyze mode (status {response.status_code})", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Error enabling analyze mode: {e}", "ERROR")
            return False
    
    def connect_telnet(self, skip_initial_read=False):
        """Connect to telnet server (activated by analyze mode)"""
        try:
            # Clean up any existing socket
            if self.telnet_socket:
                try:
                    self.telnet_socket.close()
                except:
                    pass
                self.telnet_socket = None
            
            self.telnet_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.telnet_socket.settimeout(10)
            self.telnet_socket.connect((self.device_ip, 23))
            
            if not skip_initial_read:
                # Wait for initial response and consume it
                time.sleep(2)
                try:
                    self.telnet_socket.settimeout(1)
                    initial_output = self.telnet_socket.recv(1024).decode('utf-8', errors='ignore')
                except socket.timeout:
                    pass
            else:
                # For overflow dumps, don't consume initial output
                time.sleep(1)
            
            self.telnet_socket.settimeout(10)
            self.log("Telnet connection established")
            return True
            
        except Exception as e:
            self.log(f"Failed to connect to telnet: {e}", "ERROR")
            if self.telnet_socket:
                try:
                    self.telnet_socket.close()
                except:
                    pass
                self.telnet_socket = None
            return False
    
    def execute_telnet_command(self, command, wait_time=2, debug=False):
        """Execute a telnet command and return response"""
        if not self.telnet_socket:
            self.log("No telnet connection available", "ERROR")
            return None
        
        try:
            # Send command with \r line ending (device requirement)
            cmd_bytes = (command + '\r').encode('utf-8')
            if debug:
                self.log(f"Sending: {repr(cmd_bytes)}")
            self.telnet_socket.send(cmd_bytes)
            
            # Wait for response
            time.sleep(wait_time)
            
            # Read response - try multiple times to get all data
            all_data = b''
            attempts = 0
            max_attempts = 5
            
            while attempts < max_attempts:
                try:
                    self.telnet_socket.settimeout(2)
                    data = self.telnet_socket.recv(8192)
                    if data:
                        all_data += data
                        if debug:
                            self.log(f"Received {len(data)} bytes: {repr(data[:100])}...")
                        # Check if we have more data coming
                        time.sleep(0.5)
                    else:
                        break
                except socket.timeout:
                    if attempts == 0:
                        # No data received at all
                        break
                    # Might be more data coming
                    time.sleep(0.5)
                
                attempts += 1
            
            self.telnet_socket.settimeout(10)
            response = all_data.decode('utf-8', errors='ignore')
            
            if debug and response:
                self.log(f"Total response length: {len(response)}")
                
            return response
            
        except Exception as e:
            self.log(f"Error executing command '{command}': {e}", "ERROR")
            # Mark connection as broken
            if self.telnet_socket:
                try:
                    self.telnet_socket.close()
                except:
                    pass
                self.telnet_socket = None
            return None
            
        return None
    
        
    
    def extract_hex_data(self, response):
        """Extract hex data from telnet response, handling mixed command/data packets"""
        hex_data = []
        
        # Split by different line ending combinations to handle all cases
        lines = re.split(r'\r\n|\r|\n', response)
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for lines with hex data (address followed by hex bytes)
            # Format: "00000000 99 99 96 96 3f cc 66 fc c0 33 cc 03 e5 dc 31 62"
            hex_match = re.match(r'^([0-9A-Fa-f]{8})\s+([0-9A-Fa-f\s]+)', line)
            if hex_match:
                address_str = hex_match.group(1)
                hex_part = hex_match.group(2)
                
                # Extract all 2-digit hex values from the hex part
                hex_bytes = re.findall(r'\b[0-9A-Fa-f]{2}\b', hex_part)
                
                # Convert to bytes and add to our data
                for hex_byte in hex_bytes:
                    try:
                        hex_data.append(int(hex_byte, 16))
                    except ValueError:
                        # Skip invalid hex values
                        continue
        
        return bytes(hex_data)
    
    def disable_device_logging(self, debug=False):
        """Disable device logging to prevent interference with firmware dumps"""
        self.log("Disabling device logging to prevent interference...")
        
        # Send log level disable command
        log_level_response = self.execute_telnet_command("log level=0x6c", wait_time=2, debug=debug)
        if log_level_response is not None:
            self.log("Log level command sent successfully")
        else:
            self.log("Failed to send log level command", "WARN")
        
        # Send log type disable command
        log_type_response = self.execute_telnet_command("log type=0x00", wait_time=2, debug=debug)
        if log_type_response is not None:
            self.log("Log type command sent successfully")
        else:
            self.log("Failed to send log type command", "WARN")
        
        # Brief pause to let settings take effect
        time.sleep(1)
        self.log("Device logging disabled")
        return True
    
    def test_telnet_responsiveness(self, debug=False):
        """Test if telnet is responsive with a simple command"""
        test_commands = ["p", "ip", "ver"]  # Simple commands that should respond
        
        for cmd in test_commands:
            self.log(f"Testing telnet responsiveness with command: {cmd}")
            response = self.execute_telnet_command(cmd, wait_time=3, debug=debug)
            
            if response is not None and response.strip():
                self.log(f"Telnet is responsive (command '{cmd}' returned data)")
                return True
            elif response is None:
                self.log(f"Telnet connection broken during test")
                return False
        
        self.log("Telnet connected but not responding to commands")
        return False
    
    def ensure_telnet_responsive(self, debug=False, max_retries=3):
        """Ensure telnet is connected and responsive, with auto-recovery"""
        for attempt in range(max_retries):
            if not self.telnet_socket:
                self.log(f"No telnet connection, attempting to connect (attempt {attempt + 1}/{max_retries})")
                if not self.connect_telnet():
                    # If telnet connection fails, reset analyze mode and try again
                    self.log(f"Telnet connection failed, resetting analyze mode (attempt {attempt + 1}/{max_retries})")
                    
                    # Reset analyze mode
                    if not self.enable_analyze_mode(force_toggle=True):
                        self.log("Failed to reset analyze mode")
                        continue
                    
                    # Try to connect again after reset
                    if not self.connect_telnet():
                        self.log("Failed to reconnect telnet after analyze mode reset")
                        continue
            
            # Test if telnet responds to commands
            if self.test_telnet_responsiveness(debug=debug):
                return True
            
            # Telnet is connected but not responsive - need to reset analyze mode
            self.log(f"Telnet not responsive, resetting analyze mode (attempt {attempt + 1}/{max_retries})")
            
            # Close telnet connection
            if self.telnet_socket:
                try:
                    self.telnet_socket.close()
                except:
                    pass
                self.telnet_socket = None
            
            # Reset analyze mode
            if not self.enable_analyze_mode(force_toggle=True):
                self.log("Failed to reset analyze mode")
                continue
            
            # Reconnect telnet
            if not self.connect_telnet():
                self.log("Failed to reconnect telnet after analyze mode reset")
                continue
        
        self.log("Failed to establish responsive telnet connection after all retries", "ERROR")
        return False
    
    def run_single_command(self, command, debug=False):
        """Execute a single telnet command and display result"""
        self.log(f"Executing command: {command}")
        
        # Ensure telnet is responsive before executing the command
        if not self.ensure_telnet_responsive(debug=debug):
            self.log(f"Cannot execute command - telnet not responsive", "ERROR")
            return False
        
        response = self.execute_telnet_command(command, wait_time=3, debug=debug)
        
        if response is not None:
            print(f"\nCommand: {command}")
            print("Response:")
            print("-" * 40)
            if response.strip():
                print(response)
            else:
                print("(Empty response)")
            print("-" * 40)
            return True
        else:
            self.log(f"Command failed: {command}", "ERROR")
            return False
    
    def establish_robust_connection(self, command, max_retries=3):
        """Establish a robust telnet connection and send command"""
        # First attempt: try with existing connection state (if any)
        if self.telnet_socket:
            self.log("Attempting to use existing telnet connection...")
            try:
                # Send command immediately
                cmd_bytes = (command + '\r').encode('utf-8')
                self.telnet_socket.send(cmd_bytes)
                self.log("Command sent using existing connection")
                
                # Try to get data immediately
                self.telnet_socket.settimeout(2)  # Short timeout for immediate response
                data = self.telnet_socket.recv(512)  # Small initial read
                
                if data:
                    self.log(f"SUCCESS using existing connection: {len(data)} bytes")
                    return data  # Return the first chunk of data
                else:
                    self.log("No data received on existing connection")
                    
            except Exception as e:
                self.log(f"Existing connection failed: {e}")
                # Close the broken connection
                try:
                    self.telnet_socket.close()
                except:
                    pass
                self.telnet_socket = None
        
        # Now try with fresh connections if existing didn't work
        for attempt in range(max_retries):
            self.log(f"Connection attempt {attempt + 1}/{max_retries}")
            
            # Only force reset analyze mode if this is not the first attempt
            # or if we don't have existing telnet connection
            if attempt == 0:
                # First attempt: check if analyze mode is already ON
                analyze_status = self.get_analyze_status()
                self.log(f"Current analyze status: {analyze_status}")
                
                if analyze_status != "ON":
                    self.log("Analyze mode not enabled, enabling...")
                    if not self.enable_analyze_mode():
                        self.log(f"Failed to enable analyze mode on attempt {attempt + 1}")
                        continue
                else:
                    self.log("Analyze mode already enabled")
            else:
                # Subsequent attempts: force reset analyze mode
                self.log("Resetting analyze mode for fresh start...")
                if not self.enable_analyze_mode(force_toggle=True):
                    self.log(f"Failed to reset analyze mode on attempt {attempt + 1}")
                    continue
            
            # Fresh telnet connection without consuming initial output
            if not self.connect_telnet(skip_initial_read=True):
                self.log(f"Failed to connect telnet on attempt {attempt + 1}")
                continue
            
            try:
                # Send command immediately
                cmd_bytes = (command + '\r').encode('utf-8')
                self.telnet_socket.send(cmd_bytes)
                self.log(f"Command sent on attempt {attempt + 1}")
                
                # Try to get data immediately
                self.telnet_socket.settimeout(2)  # Short timeout for immediate response
                data = self.telnet_socket.recv(512)  # Small initial read
                
                if data:
                    self.log(f"SUCCESS: Got data on attempt {attempt + 1}: {len(data)} bytes")
                    return data  # Return the first chunk of data
                else:
                    self.log(f"No data received on attempt {attempt + 1}")
                    
            except socket.timeout:
                self.log(f"Timeout on attempt {attempt + 1}")
            except Exception as e:
                self.log(f"Error on attempt {attempt + 1}: {e}")
            
            # Clean up for next attempt
            if self.telnet_socket:
                try:
                    self.telnet_socket.close()
                except:
                    pass
                self.telnet_socket = None
        
        self.log("All connection attempts failed", "ERROR")
        return None
    
    def collect_missing_rows(self, output_prefix, start_offset=0, count=1):
        """
        Collects skipped memory rows by dumping strategically chosen offsets.
        This targets the specific missing data due to the device's row-skipping bug.
        """
        self.log("Phase 0: Collecting skipped memory rows...")
        missing_data_map = {}  # Map offset to data

        # Convert start_offset to int for calculations
        if isinstance(start_offset, str):
            if start_offset.lower().startswith('0x'):
                start_offset = int(start_offset, 16)
            else:
                start_offset = int(start_offset, 16)

        # Strategy: For the main dump region, collect data that would be at the skipped 3rd row
        # The skipped row is always at (start_address + 0x20)
        critical_offsets = []
        
        # For offset 0, strategically capture one offset that covers the missing area
        if start_offset == 0:
            critical_offsets = [0x10]  # Start from 0x10 to ensure coverage
        
        # In practice, only collect one strategic offset now
        # critical_offsets.extend([0x20, 0x40])  # Removed extra captures for efficiency
        
        self.log(f"Targeting critical offset: {[hex(x) for x in critical_offsets]}")
        
        for offset in critical_offsets:
            offset_hex = f"{offset:x}"
            command = f"flash sector read={offset_hex},{count}"
            self.log(f"Collecting missing data with command: {command}")

            initial_data = self.establish_robust_connection(command)
            if not initial_data:
                self.log(f"Failed to collect data from offset 0x{offset:x}", "WARN")
                continue

            # Continue reading from the established connection to get full response
            all_data = initial_data
            try:
                while True:
                    self.telnet_socket.settimeout(2)
                    additional_data = self.telnet_socket.recv(1024)
                    if not additional_data:
                        break
                    all_data += additional_data
            except socket.timeout:
                pass  # Expected when no more data
            except Exception as e:
                self.log(f"Error reading additional data: {e}", "WARN")

            text_data = all_data.decode('utf-8', errors='ignore')
            hex_data = self.extract_hex_data(text_data)
            if hex_data:
                missing_data_map[offset] = hex_data
                self.log(f"Collected {len(hex_data)} bytes from offset 0x{offset:x}")
            
            # Small delay between commands to avoid overwhelming device
            time.sleep(2)

        # Combine missing data in order
        missing_data = bytearray()
        for offset in sorted(missing_data_map.keys()):
            missing_data.extend(missing_data_map[offset])

        # Save missing data
        missing_filename = f"{output_prefix}_missing_rows.bin"
        try:
            with open(missing_filename, 'wb') as f:
                f.write(missing_data)

            self.log(f"Missing data ({len(missing_data)} bytes) saved to: {missing_filename}")
            
            # Also save a metadata file explaining what was collected
            metadata = {
                'purpose': 'Missing row data collection (Phase 0)',
                'device_bug': 'Device skips 3rd row (offset+0x20) in flash sector reads',
                'collected_offsets': [hex(x) for x in sorted(missing_data_map.keys())],
                'total_bytes': len(missing_data),
                'timestamp': datetime.now().isoformat()
            }
            
            metadata_filename = f"{output_prefix}_missing_rows_metadata.json"
            with open(metadata_filename, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except Exception as e:
            self.log(f"Failed to save missing data: {e}", "ERROR")


    def dump_flash_region(self, start_offset, count, output_file, resume=False, debug=False):
        """
        Dump flash memory region with progress reporting
        
        Args:
            start_offset: Starting offset (hex string like 'e7' or int)
            count: Number of sectors to read (hex string like 'A' or int) 
            output_file: Output filename
            resume: Whether to resume from existing partial dump
        """
        
        # Convert parameters to appropriate format
        if isinstance(start_offset, str):
            if start_offset.lower().startswith('0x'):
                start_offset = start_offset[2:]
            offset_str = start_offset
        else:
            offset_str = f"{start_offset:x}"
            
        if isinstance(count, str):
            if count.lower().startswith('0x'):
                count = count[2:]
            count_str = count
        else:
            count_str = f"{count:x}" if count < 10 else str(count)
        
        # Check for existing dump (either partial or main file)
        partial_file = output_file.replace('.bin', '_partial.bin')
        metadata_file = output_file.replace('.bin', '_metadata.json')
        
        firmware_data = bytearray()
        current_address = 0
        resume_from_address = 0
        
        if resume and os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Check if it's an incomplete dump that can be resumed  
                if not metadata.get('completed', False):
                    # Look for existing firmware data (either partial or main file)
                    existing_file = None
                    if os.path.exists(partial_file):
                        existing_file = partial_file
                    elif os.path.exists(output_file):
                        existing_file = output_file
                    
                    if existing_file:
                        with open(existing_file, 'rb') as f:
                            firmware_data = bytearray(f.read())
                        
                        current_address = metadata.get('current_address', 0)
                        resume_from_address = len(firmware_data)  # Resume from file size (byte offset)
                        self.log(f"Resuming dump from address 0x{resume_from_address:x}, {len(firmware_data)} bytes already read")
                    else:
                        self.log("Metadata found but no data file to resume from", "WARN")
                else:
                    self.log("Dump already marked as completed, not resuming", "WARN")
            except Exception as e:
                self.log(f"Failed to load existing dump, starting fresh: {e}", "WARN")
                firmware_data = bytearray()
                current_address = 0
                resume_from_address = 0
        
        # Build flash command - for overflow dumps (count=0), use resume address as start
        if count_str == '0' and resume_from_address > 0:
            # Overflow dump with resume: start from resume address (in hex)
            resume_hex = f"{resume_from_address:x}"
            command = f"flash sector read={resume_hex},0"
            self.log(f"Resuming overflow dump from address {resume_from_address} (0x{resume_hex})")
        else:
            # Normal dump or fresh start
            command = f"flash sector read={offset_str},{count_str}"
        
        self.log(f"Starting flash dump with command: {command}")
        
        # First ensure we have a telnet connection and disable device logging
        if not self.ensure_telnet_responsive(debug=debug):
            self.log("Cannot establish telnet connection for logging disable", "ERROR")
            return False
        
        # Disable device logging before starting dump to prevent interference
        self.disable_device_logging(debug=debug)
        
        # Use robust connection establishment for all dump types
        initial_data = self.establish_robust_connection(command)
        if not initial_data:
            self.log("Failed to establish connection and start dump", "ERROR")
            return False
        
        # Process the initial data we got
        text_data = initial_data.decode('utf-8', errors='ignore')
        hex_data = self.extract_hex_data(text_data)
        if hex_data:
            firmware_data.extend(hex_data)
            self.log(f"Extracted {len(hex_data)} bytes from initial data")
        
        # Continue reading from the established connection
        self.log("Continuing data read...")
        
        # Read the continuous data stream
        bytes_read = len(firmware_data)
        bytes_skipped = 0  # Track how many bytes we've skipped during resume
        last_progress_time = time.time()
        last_progress_bytes = bytes_read
        progress_interval = 10  # Report progress every 10 seconds
        save_interval = 60  # Save progress every 60 seconds
        last_save_time = time.time()
        no_data_count = 0  # Track consecutive timeouts
        max_no_data = 3 if count_str == '0' else 1  # Allow more timeouts for overflow dumps
        
        try:
            while True:
                try:
                    # Adjust timeouts based on dump type
                    if count_str == '0':
                        self.telnet_socket.settimeout(3)  # Shorter timeout for continuous stream
                        data = self.telnet_socket.recv(1024)  # Smaller buffer
                    else:
                        self.telnet_socket.settimeout(30)  # Normal timeout for regular dumps
                        data = self.telnet_socket.recv(8192)
                    
                    if not data:
                        self.log("Connection closed by device")
                        break
                    
                    # Reset no-data counter on successful read
                    no_data_count = 0
                    
                    # Conditional debug logging for raw data
                    if debug:
                        self.log(f"DEBUG: Received {len(data)} bytes: {repr(data[:100])}...")
                    
                    # Decode and extract hex data
                    text_data = data.decode('utf-8', errors='ignore')
                    hex_data = self.extract_hex_data(text_data)
                    
                    # Debug: show first bit of text data if we're not getting hex data
                    if not hex_data and text_data.strip():
                        self.log(f"DEBUG: Received text but no hex extracted: {repr(text_data[:100])}...")
                    
                    if hex_data:
                        # Track expected address for gap detection
                        expected_next_address = current_address + len(hex_data)
                        
                        # Append hex data to firmware
                        firmware_data.extend(hex_data)
                        bytes_read = len(firmware_data)
                        current_address = expected_next_address
                        
                        if len(firmware_data) % 1000 == 0:  # Show progress every 1000 bytes
                            self.log(f"Extracted {len(hex_data)} bytes, total: {len(firmware_data)}")
                    else:
                        # Detect if a row was skipped during the process
                        if text_data.strip():  # Only warn if we got some text but no hex
                            bytes_skipped += 16  # Assuming each row is 16 bytes
                            self.log(f"Warning: Row may have been skipped at offset 0x{current_address:x}", "WARN")
                    
                    current_time = time.time()
                    if current_time - last_progress_time >= progress_interval:
                        elapsed = current_time - last_progress_time
                        bytes_since_last = bytes_read - last_progress_bytes
                        rate = bytes_since_last / elapsed if elapsed > 0 else 0
                        
                        self.log(f"Progress: {bytes_read:,} bytes read, {rate:.1f} bytes/sec")
                        
                        last_progress_time = current_time
                        last_progress_bytes = bytes_read
                    
                    # Periodic save
                    if current_time - last_save_time >= save_interval:
                        self.log("Saving progress...")
                        try:
                            with open(partial_file, 'wb') as f:
                                f.write(firmware_data)
                            
                            metadata = {
                                'device_ip': self.device_ip,
                                'command': command,
                                'current_address': current_address,
                                'bytes_read': bytes_read,
                                'timestamp': datetime.now().isoformat(),
                                'last_save': datetime.now().isoformat()
                            }
                            
                            with open(metadata_file, 'w') as f:
                                json.dump(metadata, f, indent=2)
                            
                            self.log(f"Progress saved: {bytes_read:,} bytes")
                            last_save_time = current_time
                            
                        except Exception as e:
                            self.log(f"Failed to save progress: {e}", "WARN")
                    
                except socket.timeout:
                    no_data_count += 1
                    self.log(f"Timeout waiting for data ({no_data_count}/{max_no_data})")
                    
                    if no_data_count >= max_no_data:
                        self.log("Too many consecutive timeouts - dump complete")
                        break
                    
                except Exception as e:
                    self.log(f"Error reading data: {e}", "ERROR")
                    break
        
        except KeyboardInterrupt:
            self.log("Dump interrupted by user")
            # Clean up intermediate files on cancellation
            output_prefix = output_file.replace('.bin', '')
            missing_file = f"{output_prefix}_missing_rows.bin"
            missing_metadata_file = f"{output_prefix}_missing_rows_metadata.json"
            self.clean_up_files(partial_file, metadata_file, missing_file, missing_metadata_file)
            return False
        
        # Final save
        self.log(f"Dump completed. Total bytes read: {len(firmware_data):,}")
        
        try:
            # Save final firmware file
            with open(output_file, 'wb') as f:
                f.write(firmware_data)
            
            # Save final metadata
            metadata = {
                'device_ip': self.device_ip,
                'command': command,
                'total_bytes': len(firmware_data),
                'timestamp': datetime.now().isoformat(),
                'completed': True
            }
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.log(f"Firmware saved to: {output_file}")
            
            # Clean up intermediate files if dump completed successfully
            self.clean_up_files(partial_file)
            
            return True
            
        except Exception as e:
            self.log(f"Failed to save firmware file: {e}", "ERROR")
            return False
    
    def merge_missing_rows(self, output_prefix):
        """
        Merge missing rows data into the main dump file if both exist.
        This integrates the separately collected missing data into the main firmware dump.
        
        Process:
        1. Parse main dump to identify where gaps/missing rows should be
        2. Fill gaps with zeros to maintain proper offsets 
        3. Replace zero-filled gaps with actual collected missing data when available
        4. Overwrite the main output file with the merged result
        """
        main_file = f"{output_prefix}.bin"
        missing_file = f"{output_prefix}_missing_rows.bin"
        backup_file = f"{output_prefix}_original.bin"
        
        if not os.path.exists(main_file):
            self.log(f"Main dump file not found: {main_file}", "ERROR")
            return False
            
        try:
            # Read main dump
            with open(main_file, 'rb') as f:
                main_data = f.read()
            
            # Create backup of original main file
            with open(backup_file, 'wb') as f:
                f.write(main_data)
            self.log(f"Original main dump backed up to: {backup_file}")
            
            # Read missing rows data if available
            missing_data = b''
            if os.path.exists(missing_file):
                with open(missing_file, 'rb') as f:
                    missing_data = f.read()
                self.log(f"Loaded missing rows data: {len(missing_data)} bytes")
            else:
                self.log(f"No missing rows file found, will only fill gaps with zeros", "WARN")
            
            # The device skips the 3rd row at offset 0x20 in the main dump
            # The missing row we need is at offset 0x10 in the collected missing data
            # (because the missing data was collected starting from offset 0x10)
            
            merged_data = bytearray()
            gap_fills = []  # Track what gaps we fill
            
            missing_row_position = 0x20  # Where the gap should be in the final dump
            missing_data_offset = 0x10   # Where the missing row is in the collected data
            
            if len(main_data) > missing_row_position:
                # Split the main data at the gap position
                before_gap = main_data[:missing_row_position]
                after_gap = main_data[missing_row_position:]
                
                # Look for the missing row in collected data
                replacement_row = b'\x00' * 16  # Default: fill with zeros
                
                if missing_data and len(missing_data) >= missing_data_offset + 16:
                    # Extract the missing row from the correct position in collected data
                    potential_row = missing_data[missing_data_offset:missing_data_offset + 16]
                    if not all(b == 0 for b in potential_row):  # Don't replace zeros with zeros
                        replacement_row = potential_row
                        self.log(f"Found replacement data for missing row: {replacement_row.hex()}")
                    else:
                        self.log(f"Missing row data is all zeros, using zero fill")
                else:
                    self.log(f"No missing row data available at offset 0x{missing_data_offset:x}, filling gap with zeros")
                
                # Construct merged data
                merged_data = bytearray(before_gap + replacement_row + after_gap)
                gap_fills.append({
                    'offset': missing_row_position,
                    'size': 16,
                    'filled_with': 'collected_data' if replacement_row != b'\x00' * 16 else 'zeros',
                    'replacement_data': replacement_row.hex() if replacement_row != b'\x00' * 16 else 'zeros'
                })
                
            else:
                # Main data is too short to have the expected gap
                merged_data = bytearray(main_data)
                self.log(f"Main data too short ({len(main_data)} bytes) to contain expected gap at offset 0x{missing_row_position:x}")
            
            # Overwrite the main file with merged data
            with open(main_file, 'wb') as f:
                f.write(merged_data)
            
            self.log(f"Main dump file updated with merged data: {main_file}")
            self.log(f"Final size: {len(merged_data):,} bytes (original: {len(main_data)}, gaps filled: {len(gap_fills)})")
            
            # Save merge metadata
            merge_metadata = {
                'main_file': main_file,
                'backup_file': backup_file,
                'missing_file': missing_file if os.path.exists(missing_file) else None,
                'original_bytes': len(main_data),
                'missing_data_bytes': len(missing_data),
                'final_bytes': len(merged_data),
                'gaps_filled': gap_fills,
                'merge_strategy': 'Insert missing row from collected data at correct position',
                'merge_timestamp': datetime.now().isoformat()
            }
            
            metadata_file = f"{output_prefix}_merge_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(merge_metadata, f, indent=2)
            
            return True
            
        except Exception as e:
            self.log(f"Failed to merge files: {e}", "ERROR")
            return False
    
    def clean_up_files(self, *files):
        """Remove specified files"""
        for file in files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                    self.log(f"Removed file: {file}")
                except Exception as e:
                    self.log(f"Failed to remove file {file}: {e}", "WARN")

    def close(self):
        """Clean up connections"""
        if self.telnet_socket:
            try:
                self.telnet_socket.close()
            except:
                pass
            self.telnet_socket = None

def main():
    parser = argparse.ArgumentParser(
        description='MAC-577IF2-E Firmware Dumper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute a single command
  %(prog)s <DEVICE_IP> --command "p"
  
  # Dump 32 sectors starting from offset 0
  %(prog)s <DEVICE_IP> --dump --offset 0 --count 32 --output firmware_0-32.bin
  
  # Dump entire flash using overflow trick (very slow)
  %(prog)s <DEVICE_IP> --dump --offset 0 --count A --output full_firmware.bin
  
  # Resume interrupted dump
  %(prog)s <DEVICE_IP> --dump --offset 0 --count A --output full_firmware.bin --resume
  
  # Dump AES key area
  %(prog)s <DEVICE_IP> --dump --offset e7 --count 32 --output aes_keys.bin
        """
    )
    
    parser.add_argument('device_ip', help='IP address of the MAC-577IF2-E device')
    parser.add_argument('--password', help='Admin password (uses built-in if not specified)')
    
    # Action selection
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--command', help='Execute single telnet command')
    action_group.add_argument('--dump', action='store_true', help='Dump flash memory region')
    
    # Dump parameters
    parser.add_argument('--offset', default='0', 
                       help='Starting offset for dump (hex, e.g., "e7" or "0x100")')
    parser.add_argument('--count', default='0',
                       help='Number of sectors to read (hex, e.g., "32" or "0" for default complete)')
    parser.add_argument('--output', 
                       help='Output filename (auto-generated if not specified)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume interrupted dump from partial file')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output for telnet communication')
    parser.add_argument('--collect-missing', action='store_true',
                       help='Collect missing memory rows due to device bug (phase 0)')
    
    args = parser.parse_args()
    
    # Create dumper instance
    dumper = MAC577IF2EDumper(args.device_ip, args.password)
    
    try:
        # Check device access
        if not dumper.check_device_access():
            sys.exit(1)
        
        # Initial analyze mode setup (but recovery logic will handle issues)
        dumper.enable_analyze_mode()
        
        if args.command:
            # Execute single command (includes auto-recovery logic)
            success = dumper.run_single_command(args.command, debug=args.debug)
            sys.exit(0 if success else 1)
        
        elif args.dump:
            # Generate output filename if not provided
            if not args.output:
                timestamp = int(time.time())
                args.output = f"mac577if2e_firmware_{args.device_ip}_{timestamp}.bin"
            
            # Phase 0: Collect missing rows if requested
            if args.collect_missing:
                output_prefix = args.output.replace('.bin', '')
                dumper.collect_missing_rows(output_prefix, args.offset)
            
            # Execute flash dump
            success = dumper.dump_flash_region(
                args.offset, 
                args.count, 
                args.output,
                args.resume,
                args.debug
            )
            
            # Phase 2: Merge missing rows data into main dump if both exist
            if success and args.collect_missing:
                output_prefix = args.output.replace('.bin', '')
                merge_success = dumper.merge_missing_rows(output_prefix)
                if merge_success:
                    dumper.log("Missing rows data successfully merged into main dump")
                    # Clean up intermediate files after successful merge
                    missing_file = f"{output_prefix}_missing_rows.bin"
                    missing_metadata_file = f"{output_prefix}_missing_rows_metadata.json"
                    dumper.clean_up_files(missing_file, missing_metadata_file)
                else:
                    dumper.log("Failed to merge missing rows data", "WARN")
            
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        dumper.log("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        dumper.log(f"Unexpected error: {e}", "ERROR")
        sys.exit(1)
    finally:
        dumper.close()

if __name__ == '__main__':
    main()
