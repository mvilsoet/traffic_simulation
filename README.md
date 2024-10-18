# Traffic Simulation Project

## Cloud-Native Architecture

This project implements a scalable, event-driven traffic simulation system that models vehicle movement, traffic light changes, and road conditions in a custom city. Current features are as follows:
- Dynamic traffic light control
- Road blockage simulation
- Vehicle movement that obeys lights and road closures
- 1 Hz Visualization Dashboard on localhost:8050
- 2 Event-Driven AWS SQS Queues for messaging between all modules
- Data persistence using AWS S3 (state dump) and Parquet files (initial state load)

### Modules

The system consists of four main modules:

1. **SimCore**: Holds current state of the entire simulation.
2. **AgentModule**: Manages vehicle behaviors
3. **TrafficModule**: Controls traffic lights and road conditions
4. **VisualizationModule**: Downloads the simCore state dump and displays live changes

These modules communicate asynchronously through AWS SQS queues, allowing for scalable and decoupled operations. The visualization is not yet separated from simCore (saving on storage cost, sorry).

## Prerequisites

- Python 3.8+
- AWS account with appropriate permissions
- Boto3 library
- Pandas library
- Plotly and Dash libraries for visualization

## Setup

1. Clone the repository

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Configure AWS credentials:
   - Set up your AWS credentials in `~/.aws/credentials` or use environment variables.
   - Modify bucket name in init_aws.py to your bucket.

4. Initialize the AWS resources:
   ```
   python scripts/init_aws.py
   ```

5. Update the `config/config.json` file with your specific AWS region and S3 bucket names from init_aws.py

## Running the Simulation

To start all modules of the simulation, run:

```
bash scripts/run_simulation.sh
```

This script will launch all necessary Python modules in the background.

## Visualization

Once the simulation is running, you can view the visualization by opening a web browser and navigating to:

```
http://localhost:8050
```

## Project Structure

```
traffic_simulation/
│
├── traffic_simulation/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── simCore.py
│   │   ├── agentModule.py
│   │   ├── trafficModule.py
│   │   └── visualizationModule.py
│   ├── utils/
│   │   ├── __init__.py
│   │   └── sqsUtility.py
├── config/
│   └── config.json
├── scripts/
│   ├── init_aws.py
│   └── run_simulation.sh
├── README.md
└── requirements.txt
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
