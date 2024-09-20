#!/bin/bash

# Function to handle Ctrl+C
function shutdown {
    echo ""
    echo "Shutting down simulation..."
    # Kill the background processes
    kill $SIMCORE_PID $AGENT_PID $TRAFFIC_PID
    wait $SIMCORE_PID $AGENT_PID $TRAFFIC_PID 2>/dev/null
    echo "All processes have been terminated."
    exit
}

# Trap Ctrl+C (SIGINT) and call the shutdown function
trap shutdown SIGINT

# Start SimCore
echo "Starting SimCore..."
python3 simCore.py &
SIMCORE_PID=$!

# Give SimCore a moment to initialize and send the Initialize message
sleep 2

# Start AgentModule
echo "Starting AgentModule..."
python3 agentModule.py &
AGENT_PID=$!

# Start TrafficModule
echo "Starting TrafficModule..."
python3 trafficModule.py &
TRAFFIC_PID=$!

# Wait for all background processes to finish
wait $SIMCORE_PID $AGENT_PID $TRAFFIC_PID

echo "Simulation completed."
