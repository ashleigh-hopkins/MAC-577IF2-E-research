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
            
            if current_status == "ON" or force_toggle:
                # Disable first to reset the mode
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
        for attempt in range(max_retries):
            self.log(f"Connection attempt {attempt + 1}/{max_retries}")
            
            # Force reset analyze mode before each attempt
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
    
    def dump_flash_region(self, start_offset, count, output_file, resume=False):
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
        
        # Check for existing partial dump
        partial_file = output_file.replace('.bin', '_partial.bin')
        metadata_file = output_file.replace('.bin', '_metadata.json')
        
        firmware_data = bytearray()
        current_address = 0
        
        if resume and os.path.exists(partial_file) and os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                with open(partial_file, 'rb') as f:
                    firmware_data = bytearray(f.read())
                
                current_address = metadata.get('current_address', 0)
                self.log(f"Resuming dump from address 0x{current_address:x}, {len(firmware_data)} bytes already read")
            except Exception as e:
                self.log(f"Failed to load partial dump, starting fresh: {e}", "WARN")
                firmware_data = bytearray()
                current_address = 0
        
        # Build flash command
        command = f"flash sector read={offset_str},{count_str}"
        self.log(f"Starting flash dump with command: {command}")
        
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
                    
                    # Debug: always show raw data received for troubleshooting
                    self.log(f"DEBUG: Received {len(data)} bytes: {repr(data[:100])}...")
                    
                    # Decode and extract hex data
                    text_data = data.decode('utf-8', errors='ignore')
                    hex_data = self.extract_hex_data(text_data)
                    
                    # Debug: show first bit of text data if we're not getting hex data
                    if not hex_data and text_data.strip():
                        self.log(f"DEBUG: Received text but no hex extracted: {repr(text_data[:100])}...")
                    
                    if hex_data:
                        firmware_data.extend(hex_data)
                        bytes_read = len(firmware_data)
                        current_address += len(hex_data)
                        if len(firmware_data) % 1000 == 0:  # Show progress every 1000 bytes
                            self.log(f"Extracted {len(hex_data)} bytes, total: {len(firmware_data)}")
                    
                    # Progress reporting
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
            
            # Clean up partial file if dump completed successfully
            if os.path.exists(partial_file):
                os.remove(partial_file)
            
            return True
            
        except Exception as e:
            self.log(f"Failed to save firmware file: {e}", "ERROR")
            return False
    
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
  %(prog)s 192.168.0.54 --command "p"
  
  # Dump 32 sectors starting from offset 0
  %(prog)s 192.168.0.54 --dump --offset 0 --count 32 --output firmware_0-32.bin
  
  # Dump entire flash using overflow trick (very slow)
  %(prog)s 192.168.0.54 --dump --offset 0 --count A --output full_firmware.bin
  
  # Resume interrupted dump
  %(prog)s 192.168.0.54 --dump --offset 0 --count A --output full_firmware.bin --resume
  
  # Dump AES key area
  %(prog)s 192.168.0.54 --dump --offset e7 --count 32 --output aes_keys.bin
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
    parser.add_argument('--count', default='A',
                       help='Number of sectors to read (hex, e.g., "32" or "A" for overflow)')
    parser.add_argument('--output', 
                       help='Output filename (auto-generated if not specified)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume interrupted dump from partial file')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output for telnet communication')
    
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
            
            # Execute flash dump
            success = dumper.dump_flash_region(
                args.offset, 
                args.count, 
                args.output,
                args.resume
            )
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
