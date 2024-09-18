#!/bin/bash

# Configuration
SIMULATION_DURATION=60
SQS_INIT_DELAY=2

# Function to terminate all processes
terminate_all_processes() {
    echo "Terminating all components..."
    kill $SQS_PID $CORE_PID $AGENT_PID $TRAFFIC_PID $VIZ_PID 2>/dev/null
    exit 0
}

# Set up trap to handle script interruption
trap terminate_all_processes INT TERM

# Start SQS utility
echo "Starting SQS utility..."
python3 sqsUtility.py &
SQS_PID=$!

# Give SQS utility a moment to initialize
sleep $SQS_INIT_DELAY

# Start Simulation Core
echo "Starting Simulation Core..."
python3 simCore.py &
CORE_PID=$!

# Start Agent Module
echo "Starting Agent Module..."
python3 agentModule.py &
AGENT_PID=$!

# Start Traffic Control System
echo "Starting Traffic Control System..."
python3 trafficModule.py &
TRAFFIC_PID=$!

# Start Visualization Module
echo "Starting Visualization Module..."
python3 visualizationModule.py &
VIZ_PID=$!

echo "All components started. Simulation running..."
echo "Visualization dashboard available at http://localhost:8050"
echo "Press Ctrl+C to stop the simulation and close all components."

# Wait for the specified duration
sleep $SIMULATION_DURATION

# Terminate simulation components (excluding visualization)
echo "Terminating simulation components..."
kill $SQS_PID $CORE_PID $AGENT_PID $TRAFFIC_PID 2>/dev/null

echo "Simulation completed. Visualization is still running."
echo "Press Ctrl+C to exit completely."

# Wait for visualization to finish or user to press Ctrl+C
wait $VIZ_PID
