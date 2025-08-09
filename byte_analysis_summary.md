# Mitsubishi Device Byte Analysis Summary

## Key Findings from Data Analysis (15:39-15:58)

### Group 02 (General States) - `fc620130100200000102090001000085ac28000000f5`
- **Status**: No bytes changed - completely static
- **Purpose**: General device control states (power, mode, temp, fan speed, etc.)
- **Interpretation**: Device settings remained constant during monitoring period

### Group 03 (Sensor States) - `fc620130100300000c00aaacacfe420011c6720000c3`
- **Changing Bytes**: 
  - **Position 10** (0xaa/0xac): Alternates between 170 and 172 decimal
  - **Position 18** (0x72-0x85): Incrementing counter from 114 to 133 decimal
  - **Position 21** (0xc3-0xc0): Decrementing checksum from 195 to 174 decimal

- **Parser Interpretation**:
  - Position 18 (0x72-0x85) likely maps to **room_temperature** sensor reading 
  - Position 10 could be **outside_temperature** or another sensor value
  - Position 21 appears to be a **checksum/validation** byte

### Group 04 (Error States) - `fc6201301004000000800000000000000000000000d9`
- **Status**: No bytes changed - completely static
- **Purpose**: Error reporting and abnormal state detection
- **Interpretation**: No errors detected during monitoring period

### Group 05 (Reserved/Unused) - `fc620130100500000000000000000000000000000058`  
- **Status**: No bytes changed - all zeros
- **Purpose**: Reserved or unused functionality

### Group 06 (Energy/Status States) - `fc62013010060000000100b7224f00004200000000ec`
- **Changing Bytes**:
  - **Position 11** (0x46-0x94): Highly variable from 70 to 184 decimal, mostly in 65-185 range
  - **Position 21** (0x93-0x15): Related checksum/validation byte

- **Parser Interpretation** (based on SwiCago implementation):
  - Position 11 could be **compressor frequency** (data[3] in SwiCago)
  - The values 64-184 decimal would represent compressor activity levels
  - Position 21 appears to be checksum validation

### Group 09 (Unknown) - `fc620130100900000002000000000000000000000052`
- **Status**: No bytes changed - completely static
- **Purpose**: Unknown functionality

## Potential Humidity Data Analysis

### Humidity Candidates (50-70% range typical):
- **Group 03, Position 14**: Constant value **66 decimal (0x42)** - *Strong humidity candidate*
- **Group 06, Position 11**: Variable values **64-184 decimal** - *Unlikely to be humidity*
- **Group 06, Position 16**: Constant value **66 decimal (0x42)** - *Possible humidity reading*

## Key Insights

1. **Most Likely Humidity**: Group 03, Position 14 (0x42 = 66%) appears to be a **constant humidity reading**
   - Consistent with the device being in DEHUM mode
   - Value of 66% is reasonable for indoor humidity
   - Located in sensor states group as expected

2. **Temperature Sensor Activity**: Group 03, Position 18 shows incrementing pattern
   - Could be temperature sensor readings or time-based counter
   - Increment pattern suggests active measurement system

3. **Compressor Activity**: Group 06, Position 11 shows variable patterns
   - Values fluctuate significantly (64-184)
   - Matches expected compressor frequency variations
   - Consistent with energy/operational status group

4. **Static Control States**: Groups 02, 04, 05, 09 remained completely static
   - Indicates stable device operation
   - No mode changes or errors during monitoring period

## Recommendations

1. **Add Humidity Parsing**: Implement parsing for Group 03, Position 14 as humidity sensor
2. **Validate Temperature Counter**: Investigate if Group 03, Position 18 is temperature or time counter  
3. **Confirm Compressor Data**: Verify Group 06, Position 11 as compressor frequency
4. **Monitor During Changes**: Test analysis when device mode/settings change to confirm interpretations

## Parser Code Modifications Needed

```python
def parse_sensor_states(payload: str) -> Optional[SensorStates]:
    # Add humidity parsing at position 28-29 (byte 14)
    humidity_raw = int(payload[28:30], 16) if len(payload) > 29 else None
    # Validate range and convert to percentage if needed
    humidity = humidity_raw if humidity_raw and 30 <= humidity_raw <= 100 else None
```
