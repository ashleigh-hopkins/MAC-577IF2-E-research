#!/usr/bin/env python3
"""
FC Log Analyzer - Analyze FC messages from Mitsubishi AC telnet logs

This script processes the FC messages from telnet debug logs and provides
comprehensive analysis using the FC message parser.
"""

from fc_message_parser import FCMessageParser, parse_fc_logs, analyze_patterns

# The actual FC log data from your telnet session
TELNET_LOG_DATA = """
2025/08/03_19:08:38 [Ii]FC 62 1 30 10 5 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 58 0 0 0 0
2025/08/03_19:08:39 [Ii]FC 42 1 30 10 3 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
2025/08/03_19:08:39 [Ii]FC 62 1 30 10 3 0 0 D 0 AC AE AE FE 42 0 11 C1 A4 0 0 8F 0 0 0 0
2025/08/03_19:08:39 [Ii]FC 42 1 30 10 4 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
2025/08/03_19:08:40 [Ii]FC 62 1 30 10 4 0 0 0 80 0 0 0 0 0 0 0 0 0 0 0 D9 0 0 0 0
2025/08/03_19:08:40 [Ii]FC 42 1 30 10 6 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
2025/08/03_19:08:40 [Ii]FC 62 1 30 10 6 0 0 0 0 0 4 22 47 0 0 42 0 0 0 0 A8 0 0 0 0
2025/08/03_19:08:40 [Ii]FC 42 1 30 10 9 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
2025/08/03_19:08:41 [Ii]FC 62 1 30 10 9 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 53 0 0 0 0
2025/08/03_19:08:41 [Ii]FC 62 1 30 10 2 0 0 1 3 7 0 1 0 0 85 B0 28 0 0 0 F2 0 0 0 0
2025/08/03_19:08:42 [Ii]FC 62 1 30 10 5 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 58 0 0 0 0
2025/08/03_19:08:42 [Ii]FC 62 1 30 10 3 0 0 D 0 AC AE AE FE 42 0 11 C1 A4 0 0 8F 0 0 0 0
2025/08/03_19:08:43 [Ii]FC 62 1 30 10 4 0 0 0 80 0 0 0 0 0 0 0 0 0 0 0 D9 0 0 0 0
2025/08/03_19:08:43 [Ii]FC 62 1 30 10 6 0 0 0 0 0 4 22 47 0 0 42 0 0 0 0 A8 0 0 0 0
2025/08/03_19:08:44 [Ii]FC 42 1 30 10 9 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
2025/08/03_19:08:44 [Ii]FC 62 1 30 10 9 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 53 0 0 0 0
2025/08/03_19:08:44 [Ii]FC 42 1 30 10 2 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
2025/08/03_19:08:44 [Ii]FC 62 1 30 10 2 0 0 1 3 7 0 1 0 0 85 B0 28 0 0 0 F2 0 0 0 0
2025/08/03_19:08:45 [Ii]FC 42 1 30 10 5 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
2025/08/03_19:08:45 [Ii]FC 62 1 30 10 5 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 58 0 0 0 0
2025/08/03_19:08:45 [Ii]FC 42 1 30 10 3 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
2025/08/03_19:08:45 [Ii]FC 62 1 30 10 3 0 0 D 0 AC AE AE FE 42 0 11 C1 A4 0 0 8F 0 0 0 0
2025/08/03_19:08:46 [Ii]FC 42 1 30 10 4 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
2025/08/03_19:08:46 [Ii]FC 62 1 30 10 4 0 0 0 80 0 0 0 0 0 0 0 0 0 0 0 D9 0 0 0 0
2025/08/03_19:08:46 [Ii]FC 42 1 30 10 6 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
2025/08/03_19:08:47 [Ii]FC 62 1 30 10 6 0 0 0 0 0 4 22 47 0 0 42 0 0 0 0 A8 0 0 0 0
2025/08/03_19:08:47 [Ii]FC 62 1 30 10 9 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 53 0 0 0 0
2025/08/03_19:09:02 [Ii]FC 62 1 30 10 3 0 0 D 0 AC AE AD FE 42 0 11 C1 A4 0 0 90 0 0 0 0
2025/08/03_19:09:05 [Ii]FC 62 1 30 10 3 0 0 D 0 AC AE AD FE 42 0 11 C1 A4 0 0 90 0 0 0 0
2025/08/03_19:09:12 [Ii]FC 62 1 30 10 3 0 0 D 0 AC AE AD FE 42 0 11 C1 A5 0 0 8F 0 0 0 0
2025/08/03_19:09:15 [Ii]FC 62 1 30 10 3 0 0 D 0 AC AE AD FE 42 0 11 C1 A5 0 0 8F 0 0 0 0
2025/08/03_19:09:18 [Ii]FC 62 1 30 10 3 0 0 C 0 AC AD AD FE 42 0 11 C1 A5 0 0 91 0 0 0 0
2025/08/03_19:09:21 [Ii]FC 62 1 30 10 3 0 0 C 0 AC AD AD FE 42 0 11 C1 A5 0 0 91 0 0 0 0
2025/08/03_19:09:25 [Ii]FC 62 1 30 10 3 0 0 C 0 AC AD AE FE 42 0 11 C1 A5 0 0 90 0 0 0 0
2025/08/03_19:09:28 [Ii]FC 62 1 30 10 3 0 0 C 0 AC AD AE FE 42 0 11 C1 A5 0 0 90 0 0 0 0
2025/08/03_19:09:31 [Ii]FC 62 1 30 10 3 0 0 C 0 AC AD AE FE 42 0 11 C1 A5 0 0 90 0 0 0 0
2025/08/03_19:09:34 [Ii]FC 62 1 30 10 3 0 0 C 0 AC AD AE FE 42 0 11 C1 A5 0 0 90 0 0 0 0
2025/08/03_19:09:37 [Ii]FC 62 1 30 10 3 0 0 C 0 AC AD AE FE 42 0 11 C1 A5 0 0 90 0 0 0 0
2025/08/03_19:09:41 [Ii]FC 62 1 30 10 3 0 0 D 0 AC AE AE FE 42 0 11 C1 A5 0 0 8E 0 0 0 0
2025/08/03_19:09:44 [Ii]FC 62 1 30 10 3 0 0 D 0 AC AE AE FE 42 0 11 C1 A5 0 0 8E 0 0 0 0
"""

def analyze_temperature_changes(results):
    """Analyze temperature changes over time in type 3 messages"""
    type3_messages = [r for r in results if r.get('command_type') == '03']
    
    print("\nTemperature Analysis (Type 3 Messages):")
    print("=" * 50)
    
    for i, msg in enumerate(type3_messages):
        print(f"\n{msg['timestamp']} - Message {i+1}")
        payload = msg['raw_payload'].split()
        
        # Look for temperature-related bytes
        if len(payload) >= 20:
            # Bytes that seem to change and could be temperature
            byte7 = payload[7]   # Changes between 0d and 0c
            byte10 = payload[10] # AC value
            byte11 = payload[11] # AE/AD values  
            byte12 = payload[12] # AE/AD values
            byte17 = payload[17] # A4/A5 values
            byte21 = payload[21] # 8F/90/91 values
            
            print(f"  Key bytes: [7]={byte7} [10]={byte10} [11]={byte11} [12]={byte12} [17]={byte17} [21]={byte21}")
            
            # Try to interpret temperature values
            temp_candidates = msg.get('temperature_candidates', [])
            if temp_candidates:
                print(f"  Temperature candidates: {temp_candidates}")

def analyze_command_patterns(results):
    """Analyze patterns in different command types"""
    print("\nCommand Pattern Analysis:")
    print("=" * 50)
    
    command_groups = {}
    for result in results:
        cmd = result.get('command_type', 'unknown')
        if cmd not in command_groups:
            command_groups[cmd] = []
        command_groups[cmd].append(result)
    
    for cmd, messages in command_groups.items():
        print(f"\nCommand Type {cmd}: {len(messages)} messages")
        if messages:
            first_msg = messages[0]
            print(f"  Sample payload: {first_msg['raw_payload']}")
            
            if cmd == '02':
                print("  -> Appears to be main status (power, mode, fan)")
            elif cmd == '03':
                print("  -> Appears to be sensor/temperature data")
            elif cmd == '04':
                print("  -> Contains 0x80 flag, possible sensor indicator")
            elif cmd == '05':
                print("  -> Simple status message")
            elif cmd == '06':
                print("  -> Complex sensor data")
            elif cmd == '09':
                print("  -> Binary flag data")

def main():
    print("Mitsubishi AC FC Log Analysis")
    print("=" * 60)
    
    # Parse all FC messages from the telnet log
    results = parse_fc_logs(TELNET_LOG_DATA)
    
    print(f"\nFound {len(results)} FC messages")
    
    # Basic pattern analysis
    patterns = analyze_patterns(results)
    print(f"\nMessage Distribution:")
    print(f"  Request (42): {patterns['message_types'].get('42', 0)}")
    print(f"  Response (62): {patterns['message_types'].get('62', 0)}")
    
    print(f"\nCommand Types: {patterns['command_types']}")
    
    # Detailed command analysis
    analyze_command_patterns(results)
    
    # Temperature analysis
    analyze_temperature_changes(results)
    
    # Look for interesting patterns
    print("\nInteresting Observations:")
    print("=" * 50)
    print("1. Type 3 messages contain temperature/sensor data")
    print("2. Byte 7 in type 3 changes between 0C and 0D - possible temperature indicator")
    print("3. Bytes 11-12 show AE/AD patterns - likely temperature readings")
    print("4. Byte 17 shows A4/A5 - another temperature or setpoint")
    print("5. Regular polling pattern: 5→3→4→6→9→2 then repeat")
    
    # Show some detailed examples
    print("\nDetailed Message Examples:")
    print("=" * 50)
    
    for i, result in enumerate(results[:5]):
        print(f"\nMessage {i+1}:")
        print(f"  Time: {result['timestamp']}")
        print(f"  Type: {result['message_type']} ({result['direction']})")
        print(f"  Command: {result.get('command_type', 'N/A')}")
        print(f"  Payload: {result['raw_payload']}")
        
        if 'power' in result:
            print(f"  Power: {result['power']}")
        if 'mode_raw' in result:
            print(f"  Mode: {result['mode_raw']}")
        if 'temperature_candidates' in result:
            print(f"  Temp candidates: {result['temperature_candidates']}")

if __name__ == '__main__':
    main()
