#!/usr/bin/env python3
import sys
import os
import time
import json
from datetime import datetime
import xml.etree.ElementTree as ET

# Add the local pymitsubishi directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../pymitsubishi'))

from pymitsubishi import MitsubishiAPI, MitsubishiController
from pymitsubishi.mitsubishi_parser import WindSpeed

# Constants
device_ip = "192.168.0.54"
initial_temperature = 23.0  # Start from current temp
target_temperature = 16.0
temp_decrement = 0.5
initial_fan_speed = 5  # Start with full fan speed
max_fan_speed = 5

# Initialize API
api = MitsubishiAPI(device_ip=device_ip)
# Create controller
ac = MitsubishiController(api=api)

# Get current status
print("Getting initial status...")
success = ac.fetch_status(debug=True)
if not success:
    print("Failed to fetch initial status")
    sys.exit(1)
    
status_summary = ac.get_status_summary()
print(f"Current temperature: {status_summary.get('target_temp', 'Unknown')}°C")
print(f"Current fan speed: {status_summary.get('fan_speed', 'Unknown')}")

# Calculate iterations
iterations = int((initial_temperature - target_temperature) / temp_decrement)
print(f"\nWill run {iterations} iterations, decreasing by {temp_decrement}°C each minute.")
print(f"Total runtime: {iterations} minutes")

# Open log file
log_filename = f"device_status_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
print(f"\nLogging to: {log_filename}")

log_data = []
current_temp = initial_temperature
current_fan_speed = initial_fan_speed
iteration = 0

def capture_device_data(controller, iteration, set_temp, set_fan):
    """Capture all device data including codes and profilecodes"""
    # Fetch current status 
    success = controller.fetch_status(debug=True)
    if not success:
        print("Warning: Failed to fetch status")
        return None
        
    # Get status summary
    summary = controller.get_status_summary()
    
    # Get energy state if available
    energy_data = {
        'power_watts': 0,
        'compressor_frequency': 0,
        'operating': False
    }
    
    if hasattr(controller.state, 'energy') and controller.state.energy:
        energy = controller.state.energy
        energy_data = {
            'power_watts': energy.estimated_power_watts or 0,
            'compressor_frequency': energy.compressor_frequency or 0,
            'operating': energy.operating or False
        }
    
    # Extract codes and profilecodes from the raw response
    codes = []
    profilecodes = []
    
    try:
        # Get raw response from API to extract codes
        response = api.send_status_request(debug=False)
        if response:
            root = ET.fromstring(response)
            
            # Extract all CODE values
            code_elems = root.findall('.//CODE/DATA/VALUE') or root.findall('.//CODE/VALUE')
            codes = [elem.text for elem in code_elems if elem.text]
            
            # Extract all PROFILECODE values
            profile_elems = root.findall('.//PROFILECODE/DATA/VALUE') or root.findall('.//PROFILECODE/VALUE')
            profilecodes = [elem.text for elem in profile_elems if elem.text]
    except Exception as e:
        print(f"Warning: Could not extract codes: {e}")
    
    return {
        "iteration": iteration,
        "timestamp": datetime.now().isoformat(),
        "set_temperature": set_temp,
        "set_fan_speed": set_fan,
        "actual_temperature": float(summary.get('target_temp', 0)),
        "actual_fan_speed": summary.get('fan_speed', 'Unknown'),
        "power_watts": energy_data['power_watts'],
        "compressor_frequency": energy_data['compressor_frequency'],
        "operating": energy_data['operating'],
        "codes": codes,
        "profilecodes": profilecodes
    }

# Initial status capture
print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Capturing initial state...")
log_entry = capture_device_data(ac, iteration, current_temp, current_fan_speed)
if log_entry:
    log_data.append(log_entry)
    print(f"Initial power: {log_entry['power_watts']}W")
    print(f"Initial compressor frequency: {log_entry['compressor_frequency']}Hz")
else:
    print("Failed to capture initial state")
    sys.exit(1)

try:
    while current_temp > target_temperature:
        iteration += 1
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iteration {iteration}/{iterations}")
        
        # Set temperature
        print(f"Setting temperature to {current_temp}°C...")
        ac.set_temperature(current_temp, debug=True)
        time.sleep(2)  # Brief pause for command to register
        
        # Set fan speed
        if current_fan_speed <= max_fan_speed:
            print(f"Setting fan speed to {current_fan_speed}...")
            wind_speed = WindSpeed(current_fan_speed)
            ac.set_fan_speed(wind_speed, debug=True)
            time.sleep(2)  # Brief pause for command to register
        
        # Wait for device to settle and energy readings to update
        print("Waiting 60 seconds for readings to stabilize...")
        time.sleep(56)  # Total 60 seconds with command pauses
        
        # Fetch current status
        print("Fetching current status...")
        log_entry = capture_device_data(ac, iteration, current_temp, current_fan_speed)
        if log_entry:
            log_data.append(log_entry)
        else:
            print("Warning: Failed to capture data for this iteration")
            continue
        
        # Display current readings
        print(f"Power: {log_entry['power_watts']}W (change: {log_entry['power_watts'] - log_data[0]['power_watts']}W)")
        print(f"Compressor: {log_entry['compressor_frequency']}Hz")
        print(f"Operating: {log_entry['operating']}")
        
        # Save log file after each iteration
        with open(log_filename, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        # Update for next iteration
        current_temp -= temp_decrement
        # Keep fan speed constant at max
            
except KeyboardInterrupt:
    print("\n\nMonitoring interrupted by user.")
except Exception as e:
    print(f"\nError occurred: {e}")
    import traceback
    traceback.print_exc()

# Final save
with open(log_filename, 'w') as f:
    json.dump(log_data, f, indent=2)

print(f"\n\nMonitoring complete. Data saved to {log_filename}")
print(f"Total iterations: {len(log_data)}")
print(f"\nPower consumption summary:")
print(f"  Initial: {log_data[0]['power_watts']}W")
print(f"  Final: {log_data[-1]['power_watts']}W")
print(f"  Change: {log_data[-1]['power_watts'] - log_data[0]['power_watts']}W")
