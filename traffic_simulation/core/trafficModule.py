import json
import os
import time
import pandas as pd
import boto3
from traffic_simulation.utils import sqsUtility
import random

class TrafficControlModule:
    def __init__(self):
        self.state = {
            'traffic_lights': {},
            'roads': {},
            'road_blockages': {},
        }
        self.initialized = False

        # Load configuration
        config_file = os.path.join(os.path.dirname(__file__), 'config', 'config.json')
        with open(config_file, 'r') as config_file:
            CONFIG = json.load(config_file)
            QUEUES = CONFIG.get('TRAFFIC_MOD_QUEUES', ['SimulationEvents', 'SimCoreUpdates'])
            self.MAX_NUMBER_OF_MESSAGES = CONFIG.get('MAX_NUMBER_OF_MESSAGES', 10)
            self.WAIT_TIME_SECONDS = CONFIG.get('WAIT_TIME_SECONDS', 1)
            self.S3_LINKS = CONFIG.get('S3_LINKS', {})

        self.queue_urls = sqsUtility.get_queue_urls(QUEUES)
        # AWS S3 client
        self.s3_client = boto3.client('s3')

    def poll_messages(self):
        messages = sqsUtility.receive_messages(self.queue_urls['SimulationEvents'], self.MAX_NUMBER_OF_MESSAGES)
        for message in messages:
            body = json.loads(message['Body'])
            message_type = body.get('type')
            if message_type == 'SimulationTick' and self.initialized:
                self.process_tick(body['data'])
            else:
                print(f"(TrafficControlModule) Unhandled message type: {message_type}", message)

            # Delete the message after processing
            sqsUtility.delete_message(self.queue_urls['SimulationEvents'], message['ReceiptHandle'])

    def load_initial_state(self):
        """Download Parquet files from S3 and initialize the state."""
        try:
            # Parse and download traffic lights
            traffic_lights_s3_url = self.S3_LINKS.get('traffic_lights')
            if traffic_lights_s3_url:
                print(f"Downloading traffic lights from {traffic_lights_s3_url}")
                bucket_name, key = self.parse_s3_url(traffic_lights_s3_url)
                self.s3_client.download_file(bucket_name, key, 'traffic_lights.parquet')
                traffic_lights_df = pd.read_parquet('traffic_lights.parquet')
                self.state['traffic_lights'] = traffic_lights_df.set_index('intersection_id')['state'].to_dict()
                print(f"Loaded {len(self.state['traffic_lights'])} traffic lights.")
            else:
                print("No traffic lights S3 link provided.")

            # Parse and download roads
            roads_s3_url = self.S3_LINKS.get('roads')
            if roads_s3_url:
                print(f"Downloading roads from {roads_s3_url}")
                bucket_name, key = self.parse_s3_url(roads_s3_url)
                self.s3_client.download_file(bucket_name, key, 'roads.parquet')
                roads_df = pd.read_parquet('roads.parquet')
                self.state['roads'] = roads_df.set_index('road_id').to_dict(orient='index')
                print(f"Loaded {len(self.state['roads'])} roads.")
            else:
                print("No roads S3 link provided.")

            # Parse and download road blockages
            road_blockages_s3_url = self.S3_LINKS.get('road_blockages')
            if road_blockages_s3_url:
                print(f"Downloading road blockages from {road_blockages_s3_url}")
                bucket_name, key = self.parse_s3_url(road_blockages_s3_url)
                self.s3_client.download_file(bucket_name, key, 'road_blockages.parquet')
                road_blockages_df = pd.read_parquet('road_blockages.parquet')
                self.state['road_blockages'] = road_blockages_df.set_index('road_id')['blocked'].to_dict()
                print(f"Loaded {len(self.state['road_blockages'])} road blockages.")
            else:
                print("No road blockages S3 link provided.")

            self.initialized = True
        except Exception as e:
            print(f"Error loading initial state: {e}")
            self.initialized = False  # Ensure initialized remains False on error

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
        sqsUtility.send_batch_messages(self.queue_urls['SimCoreUpdates'], batch_updates)
        print(f"TrafficControlModule sent updates to SimCore for tick {tick_data['tick_number']}")

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
    print("Starting TrafficControlModule...")

    traffic_control = TrafficControlModule()

    # Load initial state
    traffic_control.load_initial_state()

    if traffic_control.initialized:
        try:
            # Start polling messages
            while True:
                traffic_control.poll_messages()
                time.sleep(0.1)  # Small delay to prevent tight loop

        except KeyboardInterrupt:
            print("TrafficControlModule stopped by user.")
        except Exception as e:
            print(f"Error in TrafficControlModule: {e}")
        finally:
            print("TrafficControlModule shutting down.")
    else:
        print("Failed to initialize TrafficControlModule. Exiting.")
