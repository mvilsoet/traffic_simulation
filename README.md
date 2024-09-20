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
├── init_aws.py
├── run_simulation.sh
├── README.md
└── requirements.txt
```

- `simCore.py`: Central simulation controller
- `agentModule.py`: Manages vehicles in the simulation
- `trafficModule.py`: Manages traffic lights and road blockages
- `visualizationModule.py`: Handles the visualization of the simulation
- `sqsUtility.py`: Utility functions for interacting with Amazon SQS
- `config.json`: Configuration file for the simulation
- `init_aws.py`: Script that initializes S3 bucket and creates SQS queues
- `run_simulation.sh`: Script to start all simulation modules
- `requirements.txt`: Python dependencies

## Component Overview

### SimCore (simCore.py)

SimCore acts as the central simulation controller. It is responsible for:

- Initialization: Sending an Initialize message containing S3 links to the initial state data (roads, intersections, vehicles) to the SimulationEvents queue.
- Simulation Ticks: Emitting SimulationTick events at regular intervals to synchronize other modules.
- State Management: Receiving updates from other modules via the SimCoreUpdates queue and updating the internal simulation state accordingly.
- Global State Maintenance: Keeping track of the overall simulation state, including vehicle positions, traffic light states, and road blockages.

### AgentModule (agentModule.py)

The AgentModule manages the vehicles in the simulation. Its functionalities include:

- Initialization: Listening for the Initialize message from SimCore and initializing its internal state by downloading vehicle data from S3.
- Vehicle Updates: Upon receiving SimulationTick events, updating the positions of all vehicles based on their speed and road conditions.
- Communication: Sending vehicle updates (new positions, statuses) to SimCore via the SimCoreUpdates queue after each tick.
- Behavior Simulation: Simulating vehicle behaviors such as movement along roads and interactions with traffic lights and road blockages.

### TrafficModule (trafficModule.py)

The TrafficModule manages traffic control elements, including traffic lights and road blockages:

- Initialization: Listening for the Initialize message and setting up internal state by downloading traffic light and road data from S3.
- Traffic Control Updates: Updating traffic light states and road blockages on each SimulationTick.
- Communication: Sending updates about traffic lights and road blockages to SimCore via the SimCoreUpdates queue.
- Logic Implementation: Simulating the logic of traffic lights (e.g., cycle changes) and the occurrence and clearing of road blockages.

### VisualizationModule (visualizationModule.py)

The VisualizationModule is responsible for rendering the simulation state visually:

- Data Consumption: Listening to the SimulationEvents and SimCoreUpdates queues to receive the latest simulation state updates.
- Real-Time Rendering: Updating the visual representation of the simulation in real-time based on received updates.
- User Interface: Providing an interface (GUI or web-based) for users to observe the simulation.

Note: The VisualizationModule is a placeholder and would need implementation based on the desired visualization technology.

### SQS Utility (sqsUtility.py)

sqsUtility.py provides utility functions for interacting with Amazon SQS:

- Queue Management: Retrieving and caching queue URLs.
- Message Operations: Sending messages (single and batch), receiving messages, and deleting messages from queues.
- FIFO Queue Handling: Managing FIFO queue specifics like MessageGroupId and MessageDeduplicationId.
- Error Handling: Handling exceptions and logging for robust operation.

## Communication Flow

1. Initialization:
   - SimCore publishes an Initialize event to the SimulationEvents queue with S3 links to the initial state data.
   - AgentModule and TrafficModule consume the Initialize event, download the necessary data from S3, and initialize their internal states.

2. Simulation Ticks:
   - SimCore emits SimulationTick events at regular intervals to the SimulationEvents queue.
   - AgentModule and TrafficModule consume SimulationTick events and perform updates accordingly.

3. Module Updates:
   - After processing a tick:
     - AgentModule sends vehicle updates (e.g., positions) to SimCore via the SimCoreUpdates queue.
     - TrafficModule sends traffic light and road blockage updates to SimCore via the SimCoreUpdates queue.

4. State Update:
   - SimCore consumes updates from the SimCoreUpdates queue and updates its internal simulation state.

5. Visualization:
   - VisualizationModule consumes events from the SimulationEvents and SimCoreUpdates queues to maintain an up-to-date view of the simulation and update the visualization accordingly.

## Installation

### Prerequisites

- Python 3.7+
- AWS Account with access to SQS and S3 services
- AWS CLI configured with appropriate credentials

### Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### AWS Setup

Before running the simulation, set up the necessary AWS resources.

1. Configure AWS Credentials

Ensure that your AWS credentials are configured. Run:

```bash
aws configure
```

2. Initialize AWS Resources

Run the init_aws.py script to create the SQS queues and upload initial graph to S3 bucket:

```bash
python init_aws.py
```

## Usage

### Running the Simulation

Use the run_simulation.sh script to start all simulation modules:

```bash
./run_simulation.sh
```

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.
