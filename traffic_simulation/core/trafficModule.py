# traffic_simulation/core/trafficModule.py

import json
import time
import pandas as pd
import boto3
from traffic_simulation.utils import sqsUtility
import random
import logging
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class TrafficControlModule:
    def __init__(self):
        self.state = {
            'traffic_lights': {},
            'roads': {},
            'road_blockages': {},
        }
        self.initialized = False

        # Load configuration
        config_file = os.path.join(os.path.dirname(__file__), '../../config/config.json')
        with open(config_file, 'r') as config_file:
            CONFIG = json.load(config_file)
            QUEUES = CONFIG.get('TRAFFIC_MOD_QUEUES', ['SimulationEvents', 'SimCoreUpdates'])
            self.MAX_NUMBER_OF_MESSAGES = CONFIG.get('MAX_NUMBER_OF_MESSAGES', 10)
            self.WAIT_TIME_SECONDS = CONFIG.get('WAIT_TIME_SECONDS', 1)

        self.queue_urls = sqsUtility.get_queue_urls(QUEUES)
        logging.info(f"Queue URLs: {self.queue_urls}")

        # AWS S3 client
        self.s3_client = boto3.client('s3')

    def poll_messages(self):
        messages = sqsUtility.receive_messages(
            self.queue_urls['SimulationEvents'],
            self.MAX_NUMBER_OF_MESSAGES,
            self.WAIT_TIME_SECONDS
        )
        for message in messages:
            body = json.loads(message['Body'])
            message_type = body.get('type')
            logging.info(f"Received message of type: {message_type}")
            if message_type == 'Initialize':
                self.handle_initialize(body['data'])
            elif message_type == 'SimulationTick':
                if self.initialized:
                    self.process_tick(body['data'])
                else:
                    logging.warning("Received SimulationTick but module is not initialized.")
            else:
                logging.warning(f"Unhandled message type: {message_type}")

            # Delete the message after processing
            sqsUtility.delete_message(self.queue_urls['SimulationEvents'], message['ReceiptHandle'])

    def handle_initialize(self, data):
        """Initialize the module's state based on the data from SimCore."""
        logging.info("TrafficControlModule received Initialize message.")
        s3_links = data.get('s3_links')
        if s3_links:
            try:
                self.load_initial_state(s3_links)
                self.initialized = True
                logging.info("Initialized TrafficControlModule with initial state.")
            except Exception as e:
                logging.error(f"Error during initialization: {e}")
                self.initialized = False
        else:
            logging.error("No S3 links provided in Initialize message.")

    def load_initial_state(self, s3_links):
        """Download Parquet files from S3 and initialize the state."""
        # Parse and download traffic lights
        traffic_lights_s3_url = s3_links.get('traffic_lights')
        if traffic_lights_s3_url:
            self.download_and_load_parquet(
                s3_url=traffic_lights_s3_url,
                local_filename='traffic_lights.parquet',
                state_key='traffic_lights',
                index_column='intersection_id',
                value_column='state'
            )
        else:
            logging.error("No traffic lights S3 link provided.")

        # Parse and download roads
        roads_s3_url = s3_links.get('roads')
        if roads_s3_url:
            self.download_and_load_parquet(
                s3_url=roads_s3_url,
                local_filename='roads.parquet',
                state_key='roads',
                orient='index'
            )
        else:
            logging.error("No roads S3 link provided.")

        # Parse and download road blockages
        road_blockages_s3_url = s3_links.get('road_blockages')
        if road_blockages_s3_url:
            self.download_and_load_parquet(
                s3_url=road_blockages_s3_url,
                local_filename='road_blockages.parquet',
                state_key='road_blockages',
                index_column='road_id',
                value_column='blocked'
            )
        else:
            logging.error("No road blockages S3 link provided.")

    def download_and_load_parquet(self, s3_url, local_filename, state_key, index_column=None, value_column=None, orient=None):
        """Helper function to download and load Parquet files."""
        try:
            bucket_name, key = self.parse_s3_url(s3_url)
            logging.info(f"Downloading {s3_url} to {local_filename}")
            self.s3_client.download_file(bucket_name, key, local_filename)
            df = pd.read_parquet(local_filename)
            if index_column and value_column:
                self.state[state_key] = df.set_index(index_column)[value_column].to_dict()
            elif orient:
                self.state[state_key] = df.set_index(df.columns[0]).to_dict(orient=orient)
            else:
                self.state[state_key] = df.to_dict()
            logging.info(f"Loaded {state_key} from {local_filename}")
        except Exception as e:
            logging.error(f"Error loading {s3_url}: {e}")
            raise

    def parse_s3_url(self, s3_url):
        """Parse S3 URL to extract bucket name and key."""
        s3_url = s3_url.replace("s3://", "")
        bucket_name, key = s3_url.split('/', 1)
        return bucket_name, key

    def process_tick(self, tick_data):
        """Update traffic lights and road blockages, then send updates to SimCore."""
        batch_updates = []

        # Update traffic lights
        for intersection, light_state in self.state['traffic_lights'].items():
            new_state = self.change_traffic_light(intersection, light_state)
            self.state['traffic_lights'][intersection] = new_state
            batch_updates.append({
                'type': 'TRAFFIC_LIGHT_CHANGE',
                'data': {
                    'intersection': intersection,
                    'new_state': new_state
                }
            })

        # Update road blockages
        for road in self.state['roads'].keys():
            blockage_status = self.check_for_blockage(road)
            self.state['road_blockages'][road] = (blockage_status == 'blocked')
            batch_updates.append({
                'type': 'ROAD_BLOCKAGE',
                'data': {
                    'road': road,
                    'blockage_status': blockage_status
                }
            })

        # Send batch updates to SimCoreUpdates queue
        try:
            sqsUtility.send_batch_messages(self.queue_urls['SimCoreUpdates'], batch_updates)
            logging.info(f"Sent updates to SimCore for tick {tick_data['tick_number']}")
        except Exception as e:
            logging.error(f"Error sending updates to SimCore: {e}")

    def change_traffic_light(self, intersection, current_state):
        # Simple traffic light state change logic
        if current_state == 'green':
            return 'yellow'
        elif current_state == 'yellow':
            return 'red'
        elif current_state == 'red':
            return 'green'
        else:
            return 'red'  # Default to red if unknown state

    def check_for_blockage(self, road):
        # Randomly decide if the road is blocked
        return 'blocked' if random.random() < 0.1 else 'unblocked'

if __name__ == "__main__":
    logging.info("Starting TrafficControlModule...")

    traffic_control = TrafficControlModule()

    try:
        # Start polling messages
        while True:
            traffic_control.poll_messages()
            time.sleep(0.1)  # Small delay to prevent tight loop

    except KeyboardInterrupt:
        logging.info("TrafficControlModule stopped by user.")
    except Exception as e:
        logging.error(f"Error in TrafficControlModule: {e}")
    finally:
        logging.info("TrafficControlModule shutting down.")
