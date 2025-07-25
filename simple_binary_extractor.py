#!/usr/bin/env python3
"""
Simple Binary Extractor for MAC-577IF2-E

Collects flash memory data from multiple sectors and creates a binary file.
Uses direct netcat commands for maximum reliability.
"""

import subprocess
import sys
import time
import argparse

def wait_for_device(device_ip, max_wait=30):
    """Wait for device to come back online"""
    print(f"Waiting for device {device_ip} to be ready...", end="")
    
    for i in range(max_wait):
        try:
            result = subprocess.run(
                f"curl -s --connect-timeout 2 http://{device_ip}/license",
                shell=True, capture_output=True, timeout=5
            )
            if result.returncode == 0:
                print(" ✓ Ready")
                return True
        except:
            pass
        
        print(".", end="", flush=True)
        time.sleep(1)
    
    print(" ✗ Timeout")
    return False

def enable_telnet(device_ip):
    """Enable telnet access"""
    print("Enabling telnet...")
    
    try:
        result = subprocess.run(
            f'curl -u admin:me1debug@0567 -d "debugStatus=ON" http://{device_ip}/analyze',
            shell=True, capture_output=True, timeout=10
        )
        
        if result.returncode == 0:
            print("✓ Telnet enabled")
            time.sleep(3)  # Wait for telnet to activate
            return True
        else:
            print(f"✗ Failed to enable telnet: {result.stderr.decode()}")
            return False
    except Exception as e:
        print(f"✗ Error enabling telnet: {e}")
        return False

def read_flash_sector(device_ip, offset, size=32, timeout=10):
    """Read a flash sector using netcat"""
    command = f"flash sector read={offset:x},{size}"
    
    try:
        cmd = f'printf "{command}\\r" | nc {device_ip} 23'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
        else:
            return None
    except subprocess.TimeoutExpired:
        print(f"Timeout reading offset 0x{offset:x}")
        return None
    except Exception as e:
        print(f"Error reading offset 0x{offset:x}: {e}")
        return None

def extract_hex_bytes(response):
    """Extract hex bytes from telnet response"""
    hex_bytes = bytearray()
    
    if not response:
        return hex_bytes
    
    lines = response.split('\n')
    for line in lines:
        line = line.strip()
        # Look for lines that start with hex addresses
        if len(line) > 8 and all(c in '0123456789abcdefABCDEF' for c in line[:8]):
            parts = line.split()
            if len(parts) > 1:
                for part in parts[1:]:  # Skip the address part
                    if len(part) == 2 and all(c in '0123456789abcdefABCDEF' for c in part):
                        try:
                            hex_bytes.append(int(part, 16))
                        except ValueError:
                            continue
    
    return hex_bytes

def collect_firmware_data(device_ip, start_offset=0, end_offset=0x1000, sector_size=32):
    """Collect firmware data from multiple sectors"""
    print(f"Collecting firmware data from 0x{start_offset:x} to 0x{end_offset:x}")
    print(f"Sector size: {sector_size} bytes")
    print("-" * 50)
    
    firmware_data = bytearray()
    successful_reads = 0
    failed_reads = 0
    
    current_offset = start_offset
    
    while current_offset < end_offset:
        # Progress indicator
        if current_offset % (sector_size * 10) == 0:
            progress = (current_offset - start_offset) / (end_offset - start_offset) * 100
            print(f"Progress: {progress:.1f}% (offset 0x{current_offset:x}, {len(firmware_data)} bytes collected)")
        
        # Re-enable telnet periodically to handle crashes
        if current_offset % (sector_size * 5) == 0 and current_offset > start_offset:
            print("Re-enabling telnet...")
            wait_for_device(device_ip, 10)
            enable_telnet(device_ip)
        
        response = read_flash_sector(device_ip, current_offset, sector_size)
        
        if response:
            hex_data = extract_hex_bytes(response)
            if hex_data:
                firmware_data.extend(hex_data)
                successful_reads += 1
            else:
                failed_reads += 1
                print(f"No hex data at 0x{current_offset:x}")
        else:
            failed_reads += 1
            print(f"Failed to read 0x{current_offset:x}")
            
            # If we get multiple failures, try to re-enable telnet
            if failed_reads % 3 == 0:
                print("Multiple failures, trying to recover...")
                wait_for_device(device_ip, 15)
                enable_telnet(device_ip)
        
        current_offset += sector_size
        
        # Small delay to avoid overwhelming the device
        time.sleep(0.2)
    
    print(f"\nCollection complete!")
    print(f"Successful reads: {successful_reads}")
    print(f"Failed reads: {failed_reads}")
    print(f"Total data collected: {len(firmware_data)} bytes")
    
    return firmware_data

def save_binary_file(data, filename):
    """Save binary data to file"""
    try:
        with open(filename, 'wb') as f:
            f.write(data)
        print(f"Binary data saved to: {filename}")
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

def analyze_binary_data(data):
    """Perform basic analysis of the binary data"""
    print(f"\nBinary Analysis:")
    print(f"Size: {len(data)} bytes")
    
    if len(data) == 0:
        print("No data to analyze")
        return
    
    # Check for common file signatures
    if data[:4] == b'\x7fELF':
        print("Detected: ELF executable")
    elif data[:2] == b'MZ':
        print("Detected: DOS/Windows executable")
    elif data[:4] == b'\x50\x4b\x03\x04':
        print("Detected: ZIP archive")
    elif b'<!DOCTYPE' in data[:100] or b'<html' in data[:100]:
        print("Detected: HTML content")
    elif b'<?xml' in data[:100]:
        print("Detected: XML content")
    else:
        print("Unknown binary format")
    
    # Show first few bytes
    print(f"First 32 bytes (hex): {data[:32].hex()}")
    
    # Check for printable strings
    printable_chars = sum(1 for b in data[:100] if 32 <= b <= 126)
    if printable_chars > 50:
        print("High ratio of printable characters - might contain text data")
    
    # Look for null bytes (common in binary data)
    null_bytes = data.count(0)
    null_ratio = null_bytes / len(data) * 100
    print(f"Null bytes: {null_bytes} ({null_ratio:.1f}%)")

def main():
    parser = argparse.ArgumentParser(description='Simple Binary Extractor for MAC-577IF2-E')
    parser.add_argument('device_ip', help='IP address of the device')
    parser.add_argument('--start', type=lambda x: int(x, 0), default=0x0, 
                       help='Start offset (default: 0x0)')
    parser.add_argument('--end', type=lambda x: int(x, 0), default=0x1000, 
                       help='End offset (default: 0x1000)')
    parser.add_argument('--size', type=int, default=32, 
                       help='Sector size (default: 32)')
    parser.add_argument('--output', default='firmware_extract.bin', 
                       help='Output filename (default: firmware_extract.bin)')
    
    args = parser.parse_args()
    
    print(f"Simple Binary Extractor for MAC-577IF2-E")
    print(f"Target device: {args.device_ip}")
    print("=" * 50)
    
    try:
        # Wait for device to be ready
        if not wait_for_device(args.device_ip):
            print("Device not responding")
            sys.exit(1)
        
        # Enable telnet
        if not enable_telnet(args.device_ip):
            print("Failed to enable telnet")
            sys.exit(1)
        
        # Collect firmware data
        firmware_data = collect_firmware_data(
            args.device_ip, 
            args.start, 
            args.end, 
            args.size
        )
        
        if len(firmware_data) > 0:
            # Save to file
            if save_binary_file(firmware_data, args.output):
                # Analyze the data
                analyze_binary_data(firmware_data)
                print(f"\nFirmware extraction completed successfully!")
                print(f"Output file: {args.output}")
            else:
                print("Failed to save binary file")
                sys.exit(1)
        else:
            print("No firmware data was collected")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nExtraction cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
