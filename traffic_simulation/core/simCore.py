# SimCore.py

import os
import time
import json
import boto3
from traffic_simulation.utils import sqsUtility

class SimCore:
    def __init__(self):
        # Load configuration
        config_file = os.path.join(os.path.dirname(__file__), '../../config/config.json')
        with open(config_file, 'r') as config_file:
            CONFIG = json.load(config_file)
            self.QUEUES = CONFIG['QUEUES']
            self.SIMCORE_QUEUE = CONFIG.get('SIMCORE_QUEUE', 'SimulationEvents')
            self.SIMCORE_UPDATES_QUEUE = CONFIG.get('SIMCORE_UPDATES_QUEUE', 'SimCoreUpdates')
            self.MAX_NUMBER_OF_MESSAGES = CONFIG.get('MAX_NUMBER_OF_MESSAGES', 10)
            self.WAIT_TIME_SECONDS = CONFIG.get('WAIT_TIME_SECONDS', 1)
            self.TICK_INTERVAL = CONFIG.get('TICK_INTERVAL', 1)  # Time between ticks

        # Initialize SQS client
        self.queue_urls = sqsUtility.get_queue_urls(self.QUEUES)

        # Initialize the simulation state
        self.state = self.load_initial_state()

        # Send the Initialize message
        self.send_initialize_message()

        # Initialize tick counter
        self.tick_number = 0

    def load_initial_state(self):
        # Since the initial state is provided via S3 links, we assume the data is already available
        state = {
            'intersections': {},
            'roads': {},
            'traffic_lights': {},
            'vehicles': {},
            'road_blockages': {}
        }
        return state

    def send_initialize_message(self):
        # S3 links to the Parquet files (you will provide these links)
        s3_links = {
            'intersections': 's3://trafficsimulation/intersections.parquet',
            'roads': 's3://trafficsimulation/roads.parquet',
            'traffic_lights': 's3://trafficsimulation/traffic_lights.parquet',
            'vehicles': 's3://trafficsimulation/vehicles.parquet',
            'road_blockages': 's3://trafficsimulation/road_blockages.parquet'
        }

        # Send an Initialize message containing the S3 links
        initialize_message = {
            'type': 'Initialize',
            'data': {
                's3_links': s3_links
            }
        }
        sqsUtility.send_message(self.queue_urls[self.SIMCORE_QUEUE], initialize_message)
        print("Sent Initialize message with S3 links to initial state.")

    def run_simulation_loop(self):
        while True:
            # Send a SimulationTick event
            sqsUtility.send_message(self.queue_urls[self.SIMCORE_QUEUE], {
                'type': 'SimulationTick',
                'data': {'tick_number': self.tick_number}
            })
            print(f"Sent SimulationTick event for tick {self.tick_number}")

            # Wait for modules to process tick and send updates
            time.sleep(self.TICK_INTERVAL / 2)

            # Receive updates from AgentModule and TrafficControlModule
            self.receive_updates()

            # Process updates and update internal state
            self.run_simulation_step()

            # Serialize the state to a JSON file for visualization
            self.export_state()

            # Increment tick number
            self.tick_number += 1

            # Wait for the next tick
            time.sleep(self.TICK_INTERVAL / 2)

    def receive_updates(self):
        """Receive updates from AgentModule and TrafficControlModule."""
        messages = sqsUtility.receive_messages(self.queue_urls[self.SIMCORE_UPDATES_QUEUE], self.MAX_NUMBER_OF_MESSAGES)
        for message in messages:
            body = json.loads(message['Body'])
            self.process_update_message(body)
            # Delete the message from the queue
            sqsUtility.delete_message(self.queue_urls[self.SIMCORE_UPDATES_QUEUE], message['ReceiptHandle'])

    def process_update_message(self, message):
        """Process an update message and update the internal state."""
        message_type = message.get('type')
        data = message.get('data')
        if message_type == 'VehicleMoved':
            self.update_vehicle_state(data)
        elif message_type == 'TRAFFIC_LIGHT_CHANGE':
            self.update_traffic_light_state(data)
        elif message_type == 'ROAD_BLOCKAGE':
            self.update_road_blockage_state(data)
        else:
            print(f"(simCore) Unhandled message type: {message_type}")

    def update_vehicle_state(self, data):
        vehicle_id = data['vehicle_id']
        road = data['road']
        position_on_road = data['position_on_road']
        # Update the vehicle's state in the simulation
        self.state['vehicles'][vehicle_id] = {
            'road': road,
            'position': position_on_road
        }

    def update_traffic_light_state(self, data):
        intersection = data['intersection']
        new_state = data['new_state']
        # Update the traffic light state
        self.state['traffic_lights'][intersection] = new_state

    def update_road_blockage_state(self, data):
        road = data['road']
        blockage_status = data['blockage_status']
        # Update the road blockage status
        self.state['road_blockages'][road] = (blockage_status == 'blocked')

    def run_simulation_step(self):
        # Internal updates (if needed)
        pass

    def export_state(self):
        """Serialize the simulation state to a JSON file."""
        with open('sim_state.json', 'w') as f:
            json.dump(self.state, f)
        print("Exported simulation state to sim_state.json")

if __name__ == "__main__":
    print("Starting SimCore...")

    sim_core = SimCore()

    # Start the simulation loop
    sim_core.run_simulation_loop()
