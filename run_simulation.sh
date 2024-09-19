#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting Traffic Simulation modules..."

# Start each module in the background
python3 simCore.py &
python3 agentModule.py &
python3 trafficModule.py &
python3 visualizationModule.py &

# Wait for all background processes to finish
wait

echo "All modules have been started. Press Ctrl+C to stop the simulation (also kills the viz)."