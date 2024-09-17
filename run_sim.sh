#!/bin/bash

# Configuration
SIMULATION_DURATION=60
SQS_INIT_DELAY=2

# Function to terminate processes
terminate_process() {
    if [ ! -z "$1" ]; then
        kill $1 2>/dev/null
    fi
}

# Start SQS utility
echo "Starting SQS utility..."
python sqsUtility.py &
SQS_PID=$!

# Give SQS utility a moment to initialize
sleep $SQS_INIT_DELAY

# Start Simulation Core
echo "Starting Simulation Core..."
python simCore.py &
CORE_PID=$!

# Start Agent Module
echo "Starting Agent Module..."
python agentModule.py &
AGENT_PID=$!

# Start Traffic Control System
echo "Starting Traffic Control System..."
python trafficModule.py &
TRAFFIC_PID=$!

echo "All components started. Simulation running..."

# Wait for the specified duration
sleep $SIMULATION_DURATION

# Terminate all processes
echo "Terminating simulation components..."
terminate_process $SQS_PID
terminate_process $CORE_PID
terminate_process $AGENT_PID
terminate_process $TRAFFIC_PID

echo "Simulation completed."
