#!/usr/bin/env python3
"""
Resumable Binary Extractor for MAC-577IF2-E

Advanced firmware extraction with resumption capabilities and retry logic.
Saves progress and can continue from where it left off.
"""

import subprocess
import sys
import time
import argparse
import json
import os
from pathlib import Path

class ResumableExtractor:
    def __init__(self, device_ip, start_offset=0, end_offset=0x1000, sector_size=32, output_file="firmware.bin"):
        self.device_ip = device_ip
        self.start_offset = start_offset
        self.end_offset = end_offset
        self.sector_size = sector_size
        self.output_file = output_file
        self.progress_file = f"{output_file}.progress"
        self.retry_file = f"{output_file}.retry"
        
        # Progress tracking
        self.sectors_completed = set()
        self.sectors_failed = set()
        self.firmware_data = {}  # offset -> data mapping
        
        # Load existing progress if available
        self.load_progress()
    
    def save_progress(self):
        """Save current progress to file"""
        progress_data = {
            'device_ip': self.device_ip,
            'start_offset': self.start_offset,
            'end_offset': self.end_offset,
            'sector_size': self.sector_size,
            'output_file': self.output_file,
            'sectors_completed': list(self.sectors_completed),
            'sectors_failed': list(self.sectors_failed),
            'total_sectors': (self.end_offset - self.start_offset) // self.sector_size
        }
        
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save progress: {e}")
    
    def load_progress(self):
        """Load existing progress from file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    progress_data = json.load(f)
                
                # Verify parameters match
                if (progress_data.get('device_ip') == self.device_ip and
                    progress_data.get('start_offset') == self.start_offset and
                    progress_data.get('end_offset') == self.end_offset and
                    progress_data.get('sector_size') == self.sector_size):
                    
                    self.sectors_completed = set(progress_data.get('sectors_completed', []))
                    self.sectors_failed = set(progress_data.get('sectors_failed', []))
                    
                    print(f"Loaded progress: {len(self.sectors_completed)} completed, {len(self.sectors_failed)} failed")
                else:
                    print("Progress file parameters don't match, starting fresh")
            except Exception as e:
                print(f"Could not load progress: {e}")
    
    def save_binary_data(self, offset, data):
        """Save binary data for a specific offset"""
        if data:
            self.firmware_data[offset] = data
            
            # Save to partial file periodically
            if len(self.firmware_data) % 10 == 0:
                self.write_partial_binary()
    
    def write_partial_binary(self):
        """Write current firmware data to partial file"""
        partial_file = f"{self.output_file}.partial"
        try:
            with open(partial_file, 'wb') as f:
                # Write data in order by offset
                for offset in sorted(self.firmware_data.keys()):
                    f.write(self.firmware_data[offset])
        except Exception as e:
            print(f"Warning: Could not write partial file: {e}")
    
    def write_final_binary(self):
        """Write complete firmware binary file"""
        try:
            with open(self.output_file, 'wb') as f:
                total_bytes = 0
                missing_offsets = []
                
                # Write data in order, filling gaps with zeros
                current_offset = self.start_offset
                while current_offset < self.end_offset:
                    if current_offset in self.firmware_data:
                        f.write(self.firmware_data[current_offset])
                        total_bytes += len(self.firmware_data[current_offset])
                    else:
                        # Fill gap with zeros
                        f.write(b'\x00' * self.sector_size)
                        missing_offsets.append(current_offset)
                    
                    current_offset += self.sector_size
                
                print(f"Binary file written: {self.output_file}")
                print(f"Total bytes: {total_bytes}")
                if missing_offsets:
                    print(f"Missing {len(missing_offsets)} sectors (filled with zeros)")
                
                return True
        except Exception as e:
            print(f"Error writing binary file: {e}")
            return False
    
    def wait_for_device(self, max_wait=30):
        """Wait for device to come back online"""
        print(f"Waiting for device to be ready...", end="")
        
        for i in range(max_wait):
            try:
                result = subprocess.run(
                    f"curl -s --connect-timeout 2 http://{self.device_ip}/license",
                    shell=True, capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    print(" ✓")
                    return True
            except:
                pass
            
            print(".", end="", flush=True)
            time.sleep(1)
        
        print(" ✗")
        return False
    
    def disable_telnet(self):
        """Disable telnet access"""
        try:
            result = subprocess.run(
                f'curl -s -u admin:me1debug@0567 -d "debugStatus=OFF" http://{self.device_ip}/analyze',
                shell=True, capture_output=True, timeout=10
            )
            time.sleep(2)  # Wait for telnet to deactivate
            return result.returncode == 0
        except Exception:
            return False
    
    def enable_telnet(self):
        """Enable telnet access"""
        try:
            result = subprocess.run(
                f'curl -s -u admin:me1debug@0567 -d "debugStatus=ON" http://{self.device_ip}/analyze',
                shell=True, capture_output=True, timeout=10
            )
            
            if result.returncode == 0:
                time.sleep(3)  # Wait for telnet to activate
                return True
            else:
                return False
        except Exception:
            return False
    
    def reset_telnet(self):
        """Reset telnet by disabling and re-enabling"""
        print("Resetting telnet connection...")
        self.disable_telnet()
        time.sleep(5)  # Wait between disable and enable
        return self.enable_telnet()
    
    def read_flash_sector_persistent(self, offset, max_attempts=10):
        """Read a flash sector with persistent retry logic until success"""
        command = f"flash sector read={offset:x},{self.sector_size}"
        
        print(f"Reading sector 0x{offset:x}...", end="")
        
        for attempt in range(max_attempts):
            try:
                cmd = f'printf "{command}\\r" | nc {self.device_ip} 23'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0 and result.stdout.strip():
                    # Extract hex bytes from response
                    hex_data = self.extract_hex_bytes(result.stdout)
                    if hex_data:
                        print(" ✓")
                        return hex_data
                
                # Command ran but no valid data
                print(".", end="", flush=True)
                
            except subprocess.TimeoutExpired:
                print("T", end="", flush=True)  # T for timeout
            except Exception as e:
                print("E", end="", flush=True)  # E for error
            
            # Progressive retry strategies
            if attempt < max_attempts - 1:
                if attempt % 3 == 2:  # Every 3rd attempt, reset telnet
                    print("\nResetting telnet...", end="")
                    self.wait_for_device(15)
                    if self.reset_telnet():
                        print(" ✓", end="")
                    else:
                        print(" ✗", end="")
                elif attempt % 5 == 4:  # Every 5th attempt, longer wait
                    print("\nWaiting for device stability...", end="")
                    time.sleep(10)
                    self.wait_for_device(30)
                    self.enable_telnet()
                    print(" ✓", end="")
                else:
                    time.sleep(2)  # Short delay between attempts
        
        print(" ✗ FAILED")
        return None
    
    def extract_hex_bytes(self, response):
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
    
    def get_remaining_offsets(self):
        """Get list of offsets that still need to be read"""
        all_offsets = set(range(self.start_offset, self.end_offset, self.sector_size))
        remaining = all_offsets - self.sectors_completed
        return sorted(remaining)
    
    def get_failed_offsets(self):
        """Get list of failed offsets that need retry"""
        return sorted(self.sectors_failed)
    
    def extract_sectors(self, offset_list, description=""):
        """Extract data from a list of offsets"""
        if not offset_list:
            return
        
        print(f"\n{description}")
        print(f"Processing {len(offset_list)} sectors...")
        
        successful = 0
        failed = 0
        
        for i, offset in enumerate(offset_list):
            # Progress indicator
            if i % 10 == 0:
                progress = (i / len(offset_list)) * 100
                print(f"Progress: {progress:.1f}% (offset 0x{offset:x})")
            
            # Attempt to read sector with persistent retry
            data = self.read_flash_sector_persistent(offset)
            
            if data:
                self.save_binary_data(offset, data)
                self.sectors_completed.add(offset)
                self.sectors_failed.discard(offset)  # Remove from failed if it was there
                successful += 1
            else:
                self.sectors_failed.add(offset)
                failed += 1
            
            # Save progress periodically
            if (i + 1) % 5 == 0:
                self.save_progress()
            
            # Small delay
            time.sleep(0.1)
        
        print(f"Completed: {successful} successful, {failed} failed")
        self.save_progress()
    
    def run_extraction(self, retry_failed=True):
        """Run the complete extraction process"""
        print(f"Resumable Binary Extractor for MAC-577IF2-E")
        print(f"Target: {self.device_ip}")
        print(f"Range: 0x{self.start_offset:x} to 0x{self.end_offset:x}")
        print(f"Sector size: {self.sector_size} bytes")
        print(f"Output: {self.output_file}")
        print("=" * 60)
        
        # Wait for device and enable telnet
        if not self.wait_for_device():
            print("Device not responding")
            return False
        
        if not self.enable_telnet():
            print("Failed to enable telnet")
            return False
        
        # Extract new sectors
        remaining_offsets = self.get_remaining_offsets()
        if remaining_offsets:
            self.extract_sectors(remaining_offsets, "Extracting new sectors...")
        else:
            print("No new sectors to extract")
        
        # Retry failed sectors if requested
        if retry_failed:
            failed_offsets = self.get_failed_offsets()
            if failed_offsets:
                print(f"\nRetrying {len(failed_offsets)} failed sectors...")
                self.extract_sectors(failed_offsets, "Retrying failed sectors...")
            else:
                print("No failed sectors to retry")
        
        # Generate final binary
        print(f"\nGenerating final binary file...")
        total_sectors = (self.end_offset - self.start_offset) // self.sector_size
        completed = len(self.sectors_completed)
        failed = len(self.sectors_failed)
        
        print(f"Summary:")
        print(f"  Total sectors: {total_sectors}")
        print(f"  Completed: {completed} ({completed/total_sectors*100:.1f}%)")
        print(f"  Failed: {failed} ({failed/total_sectors*100:.1f}%)")
        
        if self.write_final_binary():
            print(f"\nExtraction completed!")
            print(f"Output file: {self.output_file}")
            
            # Clean up progress files if extraction was successful
            if failed == 0:
                try:
                    os.remove(self.progress_file)
                    print("Progress file cleaned up")
                except:
                    pass
            
            return True
        else:
            print("Failed to write final binary")
            return False

def main():
    parser = argparse.ArgumentParser(description='Resumable Binary Extractor for MAC-577IF2-E')
    parser.add_argument('device_ip', help='IP address of the device')
    parser.add_argument('--start', type=lambda x: int(x, 0), default=0x0, 
                       help='Start offset (default: 0x0)')
    parser.add_argument('--end', type=lambda x: int(x, 0), default=0x1000, 
                       help='End offset (default: 0x1000)')
    parser.add_argument('--size', type=int, default=32, 
                       help='Sector size (default: 32)')
    parser.add_argument('--output', default='firmware_extract.bin', 
                       help='Output filename (default: firmware_extract.bin)')
    parser.add_argument('--no-retry', action='store_true', 
                       help='Skip retrying failed sectors')
    parser.add_argument('--status', action='store_true', 
                       help='Show status of existing extraction')
    parser.add_argument('--cleanup', action='store_true', 
                       help='Clean up progress files')
    
    args = parser.parse_args()
    
    extractor = ResumableExtractor(
        args.device_ip, 
        args.start, 
        args.end, 
        args.size, 
        args.output
    )
    
    try:
        if args.status:
            # Show status
            total_sectors = (args.end - args.start) // args.size
            completed = len(extractor.sectors_completed)
            failed = len(extractor.sectors_failed)
            remaining = total_sectors - completed - failed
            
            print(f"Extraction Status for {args.output}:")
            print(f"  Range: 0x{args.start:x} to 0x{args.end:x}")
            print(f"  Total sectors: {total_sectors}")
            print(f"  Completed: {completed} ({completed/total_sectors*100:.1f}%)")
            print(f"  Failed: {failed} ({failed/total_sectors*100:.1f}%)")
            print(f"  Remaining: {remaining} ({remaining/total_sectors*100:.1f}%)")
            
            if failed > 0:
                print(f"  Failed offsets: {[hex(x) for x in sorted(extractor.sectors_failed)[:10]]}")
                if len(extractor.sectors_failed) > 10:
                    print(f"    ... and {len(extractor.sectors_failed) - 10} more")
        
        elif args.cleanup:
            # Clean up progress files
            files_to_remove = [
                extractor.progress_file,
                f"{args.output}.partial"
            ]
            
            for file in files_to_remove:
                if os.path.exists(file):
                    os.remove(file)
                    print(f"Removed {file}")
                else:
                    print(f"File {file} does not exist")
        
        else:
            # Run extraction
            success = extractor.run_extraction(retry_failed=not args.no_retry)
            if not success:
                sys.exit(1)
                
    except KeyboardInterrupt:
        print("\nExtraction cancelled by user")
        print("Progress has been saved. Use --status to check progress or resume later.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
