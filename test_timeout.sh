#!/bin/bash

# Remove old test files
rm -f test_timeout.bin*

# Start the dumper in background
python3 mac577if2e_dumper.py 192.168.0.54 --dump --offset 0 --count 0 --output test_timeout.bin --debug &
DUMPER_PID=$!

echo "Started dumper with PID: $DUMPER_PID"

# Wait for 120 seconds (2 minutes)
sleep 120

# Stop the dumper
echo "Stopping dumper..."
kill -TERM $DUMPER_PID 2>/dev/null
sleep 2
kill -KILL $DUMPER_PID 2>/dev/null

echo "Test complete. Checking results..."
