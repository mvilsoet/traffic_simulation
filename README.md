# Traffic Simulation Project

This project implements a scalable, event-driven traffic simulation system using Python and Amazon SQS for inter-component communication.

## Project Structure

```
traffic_simulation/
│
├── simCore.py
├── agentModule.py
├── trafficModule.py
├── visualizationModule.py
├── sqsUtility.py
├── config.json
├── setup_sqs_queues.sh
├── start_simulation.sh
└── README.md
```

- `simCore.py`: Central simulation controller
- `agentModule.py`: Manages vehicles in the simulation
- `trafficModule.py`: Manages traffic lights and road blockages
- `visualizationModule.py`: Handles the visualization of the simulation
- `sqsUtility.py`: Utility functions for interacting with Amazon SQS
- `config.json`: Configuration file for the simulation
- `setup_sqs_queues.sh`: Script to set up required SQS queues
- `start_simulation.sh`: Script to start all simulation modules

## Component Overview

### SimCore (simCore.py)
- Maintains the authoritative state of the entire simulation
- Processes events from all queues and updates the simulation state
- Publishes SimulationTick events to drive the simulation forward

### AgentModule (agentModule.py)
- Manages vehicles in the simulation
- Processes SimulationTick events to update vehicle positions
- Publishes VehicleCreated and VehicleMoved events

### TrafficModule (trafficModule.py)
- Manages traffic lights and road blockages
- Processes SimulationTick events to update traffic light states and road blockages
- Publishes TrafficLightChanged, RoadBlockageCreated, and RoadBlockageRemoved events

### VisualizationModule (visualizationModule.py)
- Subscribes to all events to maintain a local view of the simulation state
- Uses Dash and Plotly to create a real-time visualization of the simulation

### SQS Utility (sqsUtility.py)
- Provides utility functions for interacting with Amazon SQS
- Handles sending and receiving messages from SQS queues

## Communication Flow

1. SimCore publishes SimulationTick events to the SimulationEvents queue.
2. AgentModule and TrafficModule consume SimulationTick events:
   - AgentModule updates vehicle positions and publishes VehicleMoved events to the VehicleEvents.fifo queue.
   - TrafficModule updates traffic light states and road blockages, publishing events to the TrafficControlEvents.fifo queue.
3. SimCore consumes events from all queues (VehicleEvents.fifo, TrafficControlEvents.fifo, SimulationEvents) and updates its internal state.
4. SimCore publishes StateChanged events to the SimulationEvents queue after processing all updates.
5. VisualizationModule consumes events from all queues to maintain its local view of the simulation state and update the visualization.

## Setup and Execution

### Prerequisites
- Python 3.7+
- AWS CLI installed and configured with appropriate credentials
- Required Python packages: boto3, dash, plotly

### Setup
1. Clone the repository:
   ```
   git clone https://github.com/yourusername/traffic_simulation.git
   cd traffic_simulation
   ```

2. Install required Python packages:
   ```
   pip install boto3 dash plotly
   ```

3. Set up SQS queues:
   ```
   chmod +x setup_sqs_queues.sh
   ./setup_sqs_queues.sh
   ```

### Execution
To start the simulation:
```
chmod +x start_simulation.sh
./start_simulation.sh
```

This will start all four Python scripts (simCore.py, agentModule.py, trafficModule.py, visualizationModule.py) in parallel.

## Configuration

Ensure `config.json` contains correct settings for all modules, including SQS queue names and AWS region. All modules should load and use this configuration.

## Ensuring Proper Functionality

1. AWS Setup:
   - Ensure AWS CLI is installed and configured with appropriate credentials.
   - Run `setup_sqs_queues.sh` to create the necessary queues before first run.

2. Python Environment:
   - Ensure all required Python packages are installed (boto3, dash, plotly).
   - Consider using a virtual environment for the project.

3. Consistent Event Structures:
   - Ensure all modules use consistent event structures when publishing and consuming events.

4. Error Handling and Logging:
   - Implement robust error handling and logging in all modules to catch and report any issues.

5. Testing:
   - Implement unit tests for individual components and integration tests for the entire system.
   - Test various scenarios, including edge cases and high-load situations.

## Monitoring and Maintenance

- Monitor the AWS SQS queues during operation to ensure messages are being processed correctly and that no queue is becoming backlogged.
- Implement a graceful shutdown procedure to ensure all components can stop cleanly when the simulation is terminated.

## Future Improvements

- Implement more complex traffic rules and vehicle behaviors
- Add support for different types of vehicles (cars, buses, bicycles)
- Enhance visualization with more detailed graphics and interactivity
- Implement machine learning algorithms for traffic optimization

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

- Thanks to all contributors who have helped shape this project
- Inspired by real-world traffic simulation systems and urban planning tools

