# MAC-577IF-2E Analysis & Control Tools

A comprehensive toolkit for analyzing and controlling Mitsubishi MAC-577IF-2E WiFi air conditioner adapters.

## 🎉 Project Success

This project has achieved **two major breakthroughs**:

### ✅ **1. Firmware Extraction**
- Complete firmware dumping via telnet exploitation
- Robust extraction with crash recovery and resume capability
- Flash memory analysis with automatic gap filling

### ✅ **2. Air Conditioner Control** 
- **Full programmatic control** of Mitsubishi air conditioners
- **Working Python implementation** using the `/smart` endpoint  
- **AES encryption reverse-engineered** with static key `"unregistered"`
- **HTTP-based communication** (no ECHONET UDP needed)

---

Based on research from: https://github.com/ncaunt/meldec/issues/2

## Overview

These tools leverage discovered vulnerabilities to:
- Access admin HTTP endpoints using known credentials (`admin:me1debug@0567`)
- Enable telnet access via the `/analyze` endpoint  
- Execute diagnostic commands via telnet
- Extract firmware from flash memory with automatic recovery
- Control air conditioner functions via encrypted HTTP requests

## Tools

### 1. ac_control.py - Air Conditioner Controller ⭐

**Complete air conditioner control via HTTP `/smart` endpoint with AES encryption.**

**Core Features:**
- ✅ Device status monitoring (MAC, serial, connection status, temperatures, etc.)
- ✅ Power control (on/off)
- ✅ Temperature control (16-32°C)
- ✅ Mode control (AUTO, COOL, HEAT, DRY, FAN)
- ✅ Fan speed control (0=auto, 1-4=levels)
- ✅ ECHONET protocol activation
- ✅ Multiple output formats (table, JSON, CSV, XML)
- ✅ Debug mode with raw request/response logging

**Extended Features:**
- ✅ **Vertical vane control** (independent left/right sides: auto, v1-v5, swing)
- ✅ **Horizontal vane control** (left, center, right, combinations, swing)
- ✅ **Dehumidifier control** (adjustable level 0-100%)
- ✅ **Power saving mode** (enable/disable energy saving)
- ✅ **Buzzer control** (audio feedback control)
- ✅ **Environmental monitoring** (room & outside temperature sensors)
- ✅ **Error detection** (abnormal states and error codes)

**Basic Usage:**
```bash
# Check device status
python3 ac_control.py --ip <DEVICE_IP> --status

# Enable ECHONET protocol
python3 ac_control.py --ip <DEVICE_IP> --enable-echonet

# Basic control
python3 ac_control.py --ip <DEVICE_IP> --power on --temp 24 --mode cool --fan-speed 2

# Get status in JSON format with debug info
python3 ac_control.py --ip <DEVICE_IP> --status --format json --debug
```

**Extended Control Examples:**
```bash
# Control vanes
python3 ac_control.py --ip <DEVICE_IP> --vertical-vane v2 --vane-side right
python3 ac_control.py --ip <DEVICE_IP> --horizontal-vane c

# Adjust dehumidifier and power saving
python3 ac_control.py --ip <DEVICE_IP> --dehumidifier 75 --power-saving on

# Send buzzer command
python3 ac_control.py --ip <DEVICE_IP> --buzzer

# Combined settings
python3 ac_control.py --ip <DEVICE_IP> --power on --temp 23 --mode auto --fan-speed 1 --vertical-vane swing --horizontal-vane lr
```

### 2. mac577if2e_dumper.py - Firmware Extraction Tool

**Robust firmware extraction with automatic crash recovery and resume capability.**

**Features:**
- ✅ Complete firmware dumping via telnet commands
- ✅ Automatic device crash detection and recovery
- ✅ Resume interrupted dumps from partial files
- ✅ Progress reporting during long extractions
- ✅ Multiple dump strategies (sector-based, overflow method)
- ✅ Missing data collection and gap filling
- ✅ Single command execution for device exploration

**Usage:**
```bash
# Execute a single telnet command
python3 mac577if2e_dumper.py <DEVICE_IP> --command "p"

# Dump specific memory region (32 sectors from offset 0)
python3 mac577if2e_dumper.py <DEVICE_IP> --dump --offset 0 --count 32 --output firmware.bin

# Dump entire flash memory (very slow, but comprehensive)
python3 mac577if2e_dumper.py <DEVICE_IP> --dump --offset 0 --count 0 --output full_firmware.bin

# Resume interrupted dump
python3 mac577if2e_dumper.py <DEVICE_IP> --dump --offset 0 --count 0 --output full_firmware.bin --resume

# Dump AES key storage area
python3 mac577if2e_dumper.py <DEVICE_IP> --dump --offset e7 --count 32 --output aes_keys.bin

# Collect missing memory rows (to fill gaps in main dump)
python3 mac577if2e_dumper.py <DEVICE_IP> --dump --offset 0 --count 0 --output firmware.bin --collect-missing
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   Or use the setup script:
   ```bash
   ./setup.sh
   ```

2. **Find your device IP address:**
   - Check your router's admin panel
   - Look for devices with MAC addresses starting with `70:61:be` (Mitsubishi Electric)

3. **Test connectivity:**
   ```bash
   python3 ac_control.py --ip <DEVICE_IP> --status
   ```

## Known Working Credentials

- **Admin**: `admin:me1debug@0567` (hardcoded in firmware)
- **User**: `user:[KEY from device label]`

## Important Security Notes

- These tools exploit known vulnerabilities in the device firmware
- **Only use on devices you own** or have explicit permission to test
- The admin credentials appear to be hardcoded across all devices
- All communication is local to your network (no external servers)
- The AES encryption key `"unregistered"` is the standard key used by Mitsubishi devices

## Flash Memory Layout

Based on reverse engineering, key areas include:
- `0x0` - Firmware start
- `0xba` - WPA key storage
- `0xc4` - Domain name configuration  
- `0xc8` - ECHONET flag
- `0xe7` - AES key storage

## Device Behavior Notes

- The device may crash/reset after executing telnet commands (tools handle this automatically)
- Telnet access requires enabling via `/analyze` endpoint first
- Use `\r` line endings for telnet commands (not `\r\n`)
- Some memory rows are skipped during flash reads (tools compensate for this)

## Installation

See [INSTALL.md](INSTALL.md) for detailed installation instructions and troubleshooting.

## Reference Implementation

The `homebridge-mitsubishi-electric-aircon/` directory contains a git submodule with reference TypeScript code that helped inform this implementation.

## Contributing

Found a bug or want to add features? 
- See [CITATIONS.md](CITATIONS.md) for research references
- Check existing issues on GitHub
- All contributions welcome!

## License

This project is for educational and research purposes. Use responsibly and only on devices you own.

---

**Research Credit:** This work builds upon extensive research documented at https://github.com/ncaunt/meldec/issues/2

Special thanks to the security researchers who discovered the original vulnerabilities and documented the device's behavior.
