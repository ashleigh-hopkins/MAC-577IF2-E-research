# MELDec Repository Analysis - Insights for AC Controller Enhancement

## Overview

After analyzing the [meldec repository](https://github.com/ncaunt/meldec), I've identified several key insights that could enhance our Mitsubishi air conditioner controller. While meldec is designed for Ecodan heat pumps, there are significant protocol overlaps and architectural patterns we can leverage.

## Key Technical Insights

### 1. **Protocol Structure Similarities**

**Heat Pump Protocol (meldec):**
```
- Header: fc 62 02 7a 10 [GROUP_CODE] [DATA...] [CHECKSUM]
- Uses group codes (0x01, 0x02, 0x03, etc.) for different data types
- 22-byte fixed packet structure
- Checksum calculation: sum of bytes 1-20, then negate
- Base64 + XML double encoding for HTTP transport
```

**Our AC Protocol:**
```
- Header: fc 41 01 30 10 [GROUP_CODE] [DATA...] [CHECKSUM] 
- Similar group code system (0x01 for general control, 0x08 for extended)
- Same checksum algorithm (calc_fcc function)
- Same XML + AES encryption transport
```

**Key Insight:** The underlying packet structure is nearly identical, suggesting shared Mitsubishi protocol framework.

### 2. **Temperature Handling Patterns**

**Heat Pump Temperature Processing:**
```go
// From code_09.go and code_0b.go
temp_value = int16_value / 100.0  // Temperatures stored as int16, divided by 100
outdoor_temp = int8(raw_value/2 - 40)  // Different encoding for outdoor temps
```

**Implications for AC Controller:**
- Our current temperature handling (divide by 10) may need refinement
- Different temperature sensors may use different scaling factors
- Consider implementing temperature validation ranges per sensor type

### 3. **Group Code Architecture**

**Heat Pump Group Codes:**
```
0x01: Timestamp data
0x09: Set temperatures (zone 1, zone 2)
0x0b: Current temperatures + outdoor temp
0x0c: System temperatures (feed, return, hot water)
0x0d: Boiler temperatures
0x26: Hot water set temperature
```

**AC Controller Enhancement Opportunities:**
- Implement more granular group code handling
- Add temperature sensor differentiation
- Support for multi-zone configurations

### 4. **Device Capability Discovery**

**Heat Pump Capability Scanning:**
```go
// From main.go - scans all available group codes
gcs := []byte{
    0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x09,
    0x0b, 0x0c, 0x0d, 0x0e, 0x10, 0x11, 0x13, 0x14,
    0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1c, 0x1d,
    0x1e, 0x1f, 0x20, 0x26, 0x27, 0x28, 0x29, 0xa1, 0xa2,
}
```

**AC Enhancement Opportunity:**
- Implement systematic group code discovery
- Dynamically detect device capabilities
- Store device-specific feature maps

### 5. **Data Structure Patterns**

**Heat Pump Structured Parsing:**
```go
// From various code files
var s struct {
    SetRoomTempZone1  int16 `structs:"temperatures/indoor/set_zone1"`
    SetRoomTempZone2  int16 `structs:"temperatures/indoor/set_zone2"`
    WaterFeedTemp     int16 `structs:"temperatures/system/heating_feed"`
    WaterReturnTemp   int16 `structs:"temperatures/system/heating_return"`
    OutdoorTemp       uint8 `structs:"temperatures/outdoor/front"`
}
```

**AC Enhancement:**
- Add structured parsing for all AC data types
- Implement hierarchical data organization
- Support for multiple sensor readings

## Potential AC Controller Enhancements

### 1. **Advanced Temperature Management**

```python
class TemperatureManager:
    def __init__(self):
        self.sensor_types = {
            'room_temp': {'scale': 10, 'range': (-400, 600)},      # -40°C to 60°C  
            'outdoor_temp': {'scale': 2, 'offset': 40, 'range': (0, 255)},  # Special encoding
            'target_temp': {'scale': 10, 'range': (160, 320)},     # 16°C to 32°C
        }
    
    def decode_temperature(self, raw_value, sensor_type):
        config = self.sensor_types.get(sensor_type, {'scale': 10, 'offset': 0})
        if 'offset' in config:
            return (raw_value / config['scale']) - config['offset']
        return raw_value / config['scale']
```

### 2. **Device Capability Discovery**

```python
class DeviceCapabilityScanner:
    def __init__(self, controller):
        self.controller = controller
        self.supported_groups = []
        
    def scan_capabilities(self):
        """Scan all possible group codes to discover device features"""
        test_groups = range(0x01, 0x30) + [0xa1, 0xa2, 0xb1, 0xc1]
        
        for group in test_groups:
            try:
                # Send read request for each group
                response = self.controller.read_group_code(group)
                if response:
                    self.supported_groups.append(group)
                    self.analyze_group_structure(group, response)
            except Exception:
                continue
                
    def get_device_features(self):
        """Return discovered device capabilities"""
        features = {
            'multi_zone': 0x09 in self.supported_groups,
            'outdoor_sensor': 0x0b in self.supported_groups,  
            'advanced_vanes': 0x15 in self.supported_groups,
            'energy_monitoring': 0xa1 in self.supported_groups,
        }
        return features
```

### 3. **Enhanced Protocol Handling**

```python
class ProtocolHandler:
    @staticmethod
    def create_read_command(group_code):
        """Create read command for specific group code"""
        # Based on meldec packet structure
        packet = [0xfc, 0x42, 0x02, 0x7a, 0x10, group_code]
        packet.extend([0x00] * 15)  # Pad to 21 bytes
        packet.append(ProtocolHandler.calc_checksum(packet[1:]))
        return bytes(packet)
    
    @staticmethod
    def calc_checksum(data):
        """Calculate checksum using meldec algorithm"""
        return (-sum(data)) & 0xFF
```

### 4. **Multi-Zone Support**

```python
class MultiZoneController:
    def __init__(self, base_controller):
        self.base = base_controller
        self.zones = {}
        
    def set_zone_temperature(self, zone_id, temperature):
        """Set temperature for specific zone"""
        if zone_id == 1:
            # Use group 0x09 data structure
            return self.base.send_zone_command(0x09, {
                'zone1_temp': int(temperature * 100),
                'zone2_temp': self.zones.get(2, {}).get('target_temp', 2000)
            })
```

## Recommended Implementation Priority

1. **High Priority:**
   - Implement device capability scanning
   - Add temperature sensor differentiation
   - Enhance error handling and validation

2. **Medium Priority:**
   - Add support for reading additional group codes
   - Implement structured data parsing
   - Add multi-zone temperature control

3. **Low Priority:**
   - Energy monitoring features (if supported)
   - Advanced diagnostic capabilities
   - Historical data logging

## Key Files to Reference

- `internal/pkg/decoder/codes/code_*.go` - Data structure definitions
- `cmd/meldec/main.go` - Group code scanning logic  
- `internal/pkg/decoder/codes/checksum.go` - Checksum algorithms
- `internal/pkg/doc/doc.go` - XML protocol handling

## Conclusion

The meldec repository provides valuable insights into Mitsubishi's protocol architecture. While designed for heat pumps, the core protocol patterns are highly applicable to air conditioner control. The most valuable enhancements would be:

1. **Systematic capability discovery** to detect device-specific features
2. **Enhanced temperature handling** with proper sensor differentiation  
3. **Structured data parsing** for better device state management
4. **Multi-zone support** where hardware permits

These enhancements would make our AC controller more robust, feature-complete, and adaptable to different Mitsubishi device variants.
