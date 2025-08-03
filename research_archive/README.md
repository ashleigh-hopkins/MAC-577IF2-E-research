# Mitsubishi AC Device Code Analysis Research

This archive contains research scripts and data from analyzing Mitsubishi air conditioner device codes and their correlation with energy consumption patterns.

## Research Summary

### Objective
To identify which bytes in the raw device CODE and PROFILECODE hex strings correlate with actual power consumption (~600W measured externally vs ~144W reported by device).

### Key Findings

1. **Operating Status Detection**: CODE[4] byte 9 changes from 0x00 to 0x01 when the device transitions from idle to operating state.

2. **Potential Energy-Related Bytes**:
   - **CODE[1] bytes 10-11**: Values change when operating status changes (170-171 decimal range)
   - **CODE[1] byte 20**: Shows variations (102-106 decimal range) that might correlate with energy
   - **CODE[4] byte 12**: Changes from 0x45 to 0x46 (69-70 decimal) during operation

3. **Temperature-Related Bytes (excluded from energy analysis)**:
   - CODE[0] bytes 9, 15, 20: Clear temperature correlation patterns
   - CODE[1] byte 17: Incremental temperature counter
   - CODE[4] bytes 10, 20: Temperature-related variations

4. **PROFILECODE**: No changes detected across all test iterations - likely static configuration data.

### Test Conditions
- Temperature range: 23.0°C down to 16.5°C
- Fan speed: Fixed at maximum (level 5)
- Duration: 15 iterations over ~15 minutes
- Power consumption reported: 10W (idle) to 144.7W (operating)
- Actual power consumption (external monitor): ~600W

### Files in Archive

#### Scripts
- `log_device_status.py`: Main logging script for capturing device states and raw codes
- `analyze_hex_changes.py`: Analysis script to identify changing bytes in hex codes
- `analyze_device_logs.py`: Earlier analysis script for correlating codes with device parameters

#### Data
- `device_status_log_20250803_153255.json`: Initial short test data
- `device_status_log_20250803_153910.json`: Full 15-iteration dataset

### Next Steps for Implementation
The identified bytes (CODE[1] bytes 10-11, 20 and CODE[4] byte 12) could be used to:
1. Create a more accurate power estimation algorithm
2. Detect actual compressor operation vs idle state
3. Implement energy monitoring in Home Assistant integration

### Technical Notes
- Device communication uses pymitsubishi library
- Raw codes extracted from decrypted XML responses
- Analysis excludes known temperature-related bytes to focus on energy correlation
- Power estimation algorithm in current implementation underestimates actual consumption by ~4x

---
*Research conducted: August 3, 2025*
*Device: Mitsubishi AC at 192.168.0.54*
