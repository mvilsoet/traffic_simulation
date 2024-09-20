#!/bin/bash

# Activate virtual environment if using one (uncomment and adjust if needed)
# source venv/bin/activate

# Navigate to the root directory of the project
cd "$(dirname "$0")/.."

# Run the modules
python -m traffic_simulation.core.simCore &
python -m traffic_simulation.core.agentModule &
python -m traffic_simulation.core.trafficModule &
# python -m traffic_simulation.core.visualizationModule &

# Wait for all background processes to finish
wait
