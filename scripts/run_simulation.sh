#!/bin/bash

# Activate virtual environment if using one (uncomment and adjust if needed)
# source venv/bin/activate

# Navigate to the root directory of the project
cd "$(dirname "$0")/.."

# Function to kill background processes on exit
cleanup() {
    echo "Stopping background processes..."
    # Send SIGTERM to all child processes
    pkill -P $$
}

# Trap SIGINT (Ctrl+C) and SIGTERM signals and call cleanup
trap cleanup SIGINT SIGTERM

# Run the modules in the background and store their PIDs
python3 -m traffic_simulation.core.simCore &
SIMCORE_PID=$!

python3 -m traffic_simulation.core.agentModule &
AGENT_PID=$!

python3 -m traffic_simulation.core.trafficModule &
TRAFFIC_PID=$!

# Uncomment if you have the visualization module
# python3 -m traffic_simulation.core.visualizationModule &
# VISUALIZATION_PID=$!

# Wait for all background processes to finish
wait $SIMCORE_PID $AGENT_PID $TRAFFIC_PID
# If visualization module is used, include its PID:
# wait $SIMCORE_PID $AGENT_PID $TRAFFIC_PID $VISUALIZATION_PID