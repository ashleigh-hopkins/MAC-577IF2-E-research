# MAC-577IF2-E Firmware Reader

This project provides tools to read firmware from Mitsubishi MAC-577IF2-E WiFi adapters by leveraging the admin HTTP interface and telnet access discovered through reverse engineering research.

## Background

Based on extensive research documented in [GitHub Issue #2](https://github.com/ncaunt/meldec/issues/2), this project implements the discovered methods to:

1. Access the admin HTTP interface using credentials found in the firmware
2. Enable "analyze mode" which activates telnet access  
3. Use telnet to execute flash reading commands to extract firmware

## Key Findings from Research

- **Admin Access**: Username `user` with the `KEY` from device label works for `/config` endpoint
- **Analyze Mode**: Posting to `/analyze` with `debugStatus=on` enables telnet
- **Flash Commands**: `flash sector read=offset,size` commands work via telnet
- **Line Ending Issue**: Telnet commands need `\r` instead of `\r\n` line endings
- **NVRAM Locations**: Important data at specific offsets (AES key at 0xe7, domain at 0xc4, etc.)

## Prerequisites

- Python 3.6+
- `requests` library (`pip install requests`)
- Network access to your MAC-577IF2-E device
- The device's admin password (KEY from device label)

## Files

1. **`mac577if2e_test.py`** - Basic connectivity and access test
2. **`mac577if2e_firmware_reader.py`** - Full firmware extraction tool
3. **`README_MAC577IF2E.md`** - This documentation

## Usage

### Step 1: Test Basic Connectivity

First, verify your device is accessible and you have the correct admin password:

```bash
python3 mac577if2e_test.py 192.168.0.54 YOUR_DEVICE_KEY
```

Replace:
- `192.168.0.54` with your device's IP address
- `YOUR_DEVICE_KEY` with the KEY printed on your device label

Expected output for working setup:
```
MAC-577IF2-E Device Test
========================================
Device IP: 192.168.0.54
Password: **********

Testing connectivity to 192.168.0.54...
✓ Device is reachable via HTTP
✓ /license endpoint accessible (status: 200)

Testing admin endpoints with password...
✓ /config - accessible
✓ /analyze - accessible
✓ /server - accessible
✓ /service - accessible
✓ /unitinfo - accessible

Testing telnet connectivity...
✗ Telnet port (23) is closed

========================================
TEST SUMMARY:
✓ Device connectivity: OK
✓ Admin endpoints accessible: 5
  Accessible endpoints: /config, /analyze, /server, /service, /unitinfo
✗ Telnet: Not available
  → You need to enable analyze mode first to activate telnet

✓ /analyze endpoint is accessible!
  → You can use this to enable telnet access
  → Run the full firmware reader script next
```

### Step 2: Extract Firmware

If the test passes, proceed with firmware extraction:

```bash
python3 mac577if2e_firmware_reader.py 192.168.0.54 --password YOUR_DEVICE_KEY
```

Or run interactively (you'll be prompted for the password):

```bash
python3 mac577if2e_firmware_reader.py 192.168.0.54
```

The script will:

1. Verify admin access
2. Enable analyze mode via `/analyze` endpoint
3. Wait for telnet to become available
4. Connect to telnet and test flash commands
5. Optionally dump the full firmware

### Step 3: Analyze Results

The script will create a firmware dump file like:
```
mac577if2e_firmware_192.168.0.54_1640995200.bin
```

You can analyze this with tools like:
- `binwalk` - Firmware analysis tool
- `strings` - Extract readable strings
- `hexdump` - View hex content
- IDA Pro/Ghidra - Reverse engineering tools

## Important Notes

### Security Warning
- This process accesses debug/admin functionality on your device
- Only use on devices you own
- The process may temporarily disrupt device operation
- Consider backing up any device settings before proceeding

### Device Password
The admin password is the "KEY" value printed on your device label. This is typically:
- A string of alphanumeric characters
- Located on a sticker on the WiFi adapter
- Same as the default WiFi password for device setup

### Telnet Line Endings
The research discovered that the telnet interface expects `\r` line endings instead of the standard `\r\n`. The script handles this automatically.

### Flash Memory Layout
Based on research, important data is stored at specific NVRAM offsets:
- `0xBA`: Device WPA Key  
- `0xC4`: Melcloud domain name
- `0xE7`: AES key for `/smart` endpoint (16 bytes)
- `0xEB`: Alternative certificate/CA
- `0xFD`: "Use alternative" flag

## Troubleshooting

### "Failed to access admin interface"
- Verify device IP address is correct
- Check that you're using the correct KEY from device label
- Ensure device is on same network segment

### "Failed to enable analyze mode"  
- Device firmware may not support this method
- Try different admin credentials if available
- Some firmware versions may have different endpoints

### "Failed to connect to telnet"
- Analyze mode may not have activated telnet
- Wait longer (try 10-30 seconds) before connecting
- Some devices may require multiple attempts

### "No valid response at offset"
- This is normal when reaching end of flash memory
- Earlier sectors should contain valid firmware data
- Flash size varies by device version

## Known Issues

1. **Firmware Variations**: Different firmware versions may behave differently
2. **Device Stability**: Some devices may become unresponsive during operation
3. **Incomplete Extraction**: Not all firmware areas may be readable
4. **Network Timing**: Telnet activation timing varies between devices

## Research Attribution

This work is based on extensive community research documented in:
- [GitHub Issue #2 - ncaunt/meldec](https://github.com/ncaunt/meldec/issues/2)
- Research contributions from: @thxer, @niobos, @dragonbane0, @mafredri, and others

Key discoveries:
- @thxer: Original firmware sharing and password discovery
- @dragonbane0: Protocol analysis and endpoint documentation  
- @mafredri: Recent flash reading command discovery
- @niobos: Detailed firmware analysis and blogging

## Legal Notice

This tool is for educational and research purposes only. Use only on devices you own. The authors are not responsible for any damage to your devices or networks.

## Contributing

If you discover improvements or encounter issues:
1. Test thoroughly on your own devices first
2. Document your findings clearly
3. Submit issues/PRs with detailed information
4. Reference the original research thread when possible

## License

This project builds upon community research and is shared for educational purposes. Respect the original researchers' contributions and use responsibly.
