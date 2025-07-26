# Installation Guide - MAC-577IF-2E Air Conditioner Controller

This guide will help you set up and use the Mitsubishi MAC-577IF-2E air conditioner controller tools.

## 📋 Prerequisites

- **Python 3.7+** (for dataclasses support)
- **Network access** to your Mitsubishi air conditioner
- **Basic terminal/command line knowledge**

## 🚀 Quick Start

### 1. Clone the Repository

```bash
# Clone with submodules (recommended)
git clone --recursive https://github.com/ashleigh-hopkins/MAC-577IF2-E-research.git
cd MAC-577IF2-E-research

# OR clone normally and then initialize submodules
git clone https://github.com/ashleigh-hopkins/MAC-577IF2-E-research.git
cd MAC-577IF2-E-research
git submodule update --init --recursive
```

### 2. Install Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 3. Find Your Air Conditioner's IP Address

You can find this in your router's admin panel or use network scanning tools:

```bash
# Example methods to find device IP:
nmap -sn 192.168.1.0/24  # Scan your network
arp -a                   # Show ARP table
```

Look for a device with MAC address starting with `70:61:be` (Mitsubishi Electric).

### 4. Test Connection

```bash
python3 ac_control.py --ip <DEVICE_IP> --status
```

Replace `<DEVICE_IP>` with your air conditioner's IP address.

## 📖 Usage Examples

### Basic Operations

```bash
# Check device status
python3 ac_control.py --ip <DEVICE_IP> --status

# Enable ECHONET protocol
python3 ac_control.py --ip <DEVICE_IP> --enable-echonet

# Control the air conditioner
python3 ac_control.py --ip <DEVICE_IP> --power on --temp 24 --mode cool

# Set fan speed  
python3 ac_control.py --ip <DEVICE_IP> --fan-speed 2
```

### Different Output Formats

```bash
# JSON output (great for scripts)
python3 ac_control.py --ip <DEVICE_IP> --status --format json

# CSV output (for spreadsheets)
python3 ac_control.py --ip <DEVICE_IP> --status --format csv

# XML output
python3 ac_control.py --ip <DEVICE_IP> --status --format xml

# Table output (default, human-readable)
python3 ac_control.py --ip <DEVICE_IP> --status --format table
```

### Debug Mode

```bash
# Enable debug mode to see detailed communication
python3 ac_control.py --ip <DEVICE_IP> --status --debug
```

## 🔧 Available Commands

### Status Commands
- `--status` - Fetch and display current device status
- `--enable-echonet` - Enable ECHONET protocol on device

### Control Commands  
- `--power {on,off}` - Turn air conditioner on/off
- `--temp TEMP` - Set target temperature in Celsius (e.g., 24.5)
- `--mode {auto,cool,heat,dry,fan}` - Set operating mode
- `--fan-speed {0,1,2,3,4}` - Set fan speed (0=auto, 1-4=levels)

### Output Options
- `--format {table,csv,json,xml}` - Choose output format
- `--debug` - Show detailed debug information

## 📊 Sample Output

### Status Command (Table Format)
```
Device Information:
--------------------
  MAC: 70:61:be:xx:xx:xx
  SERIAL: xxxxxxxxxx
  CONNECT: ON
  STATUS: NORMAL
  APP_VER: 37.00
  RSSI: -26
  ECHONET: ON

LED Status:
-----------
  LED1: 0:1,0:1
  LED2: 1:5,0:45
```

### Status Command (JSON Format)
```json
{
  "mac": "70:61:be:xx:xx:xx",
  "serial": "xxxxxxxxxx",
  "connect": "ON",
  "status": "NORMAL",
  "rssi": "-26",
  "echonet": "ON"
}
```

## 🛠️ Troubleshooting

### Connection Issues

**Problem**: `✗ Failed to connect to device`

**Solutions**:
1. Verify the IP address is correct
2. Ensure device is on the same network
3. Check firewall settings
4. Try enabling ECHONET first: `--enable-echonet`

### Python Environment Issues

**Problem**: `ModuleNotFoundError`

**Solution**:
```bash
# Make sure you're in the virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Reinstall requirements
pip install -r requirements.txt
```

**Problem**: `SyntaxError` or `dataclasses` not found

**Solution**: Upgrade to Python 3.7+
```bash
python3 --version  # Check version
# If < 3.7, install newer Python version
```

### Network Discovery

**Problem**: Can't find device IP

**Solutions**:
1. Check router admin panel (usually 192.168.1.1 or 192.168.0.1)
2. Use network scanner:
   ```bash
   # Install nmap if needed
   brew install nmap  # macOS
   sudo apt install nmap  # Ubuntu/Debian
   # Scan network
   nmap -sn 192.168.1.0/24
   ```
3. Look for devices with MAC addresses starting with `70:61:be`

## 🔒 Security Notes

- This tool communicates with your air conditioner using the same encrypted protocol as the official mobile app
- All communication is local to your network
- The encryption key (`"unregistered"`) is the standard key used by Mitsubishi devices
- No data is sent to external servers

## 📚 Additional Tools

### Firmware Dumper
If you're interested in firmware analysis:

```bash
python3 mac577if2e_dumper.py --ip <DEVICE_IP>
```

See `README.md` for detailed firmware analysis documentation.

## 🤝 Contributing

Found a bug or want to add features? See `INTEGRATION_SUCCESS.md` for technical details and `CITATIONS.md` for references.

## 📄 License

This project is for educational and research purposes. See repository license for details.

---

**Need help?** Check the [GitHub Issues](https://github.com/ashleigh-hopkins/MAC-577IF2-E-research/issues) or create a new issue with:
- Your Python version (`python3 --version`)
- Operating system
- Full error message
- Device model (if known)
