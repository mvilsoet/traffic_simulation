import json
import os
import time
import pandas as pd
import boto3
from traffic_simulation.utils import sqsUtility

class AgentModule:
    def __init__(self):
        self.vehicles = {}  # Stores vehicles with their positions and states
        self.initialized = False

        # Load configuration
        config_file = os.path.join(os.path.dirname(__file__), 'config', 'config.json')
        with open(config_file, 'r') as config_file:
            CONFIG = json.load(config_file)
            QUEUES = CONFIG.get('AGENT_MOD_QUEUES', ['SimulationEvents', 'SimCoreUpdates'])
            self.MAX_NUMBER_OF_MESSAGES = CONFIG.get('MAX_NUMBER_OF_MESSAGES', 10)
            self.WAIT_TIME_SECONDS = CONFIG.get('WAIT_TIME_SECONDS', 1)
            self.S3_LINKS = CONFIG.get('S3_LINKS', {})

        self.queue_urls = sqsUtility.get_queue_urls(QUEUES)
        # AWS S3 client
        self.s3_client = boto3.client('s3')

    def process_messages(self):
        try:
            messages = sqsUtility.receive_messages(self.queue_urls['SimulationEvents'], self.MAX_NUMBER_OF_MESSAGES)
            for message in messages:
                event = json.loads(message['Body'])
                event_type = event.get('type')
                if event_type == 'SimulationTick' and self.initialized:
                    self.process_tick(event['data'])
                else:
                    print(f"(AgentModule) Unhandled event type: {event_type}")

                # Delete the message from the queue
                sqsUtility.delete_message(self.queue_urls['SimulationEvents'], message['ReceiptHandle'])
        except Exception as e:
            print(f"(AgentModule) Error processing messages: {e}")

    def load_initial_state(self):
        """Download Parquet files from S3 and initialize vehicles."""
        try:
            vehicles_s3_url = self.S3_LINKS.get('vehicles')
            if vehicles_s3_url:
                print(f"Downloading vehicles data from {vehicles_s3_url}")
                # Parse the S3 URL
                bucket_name, key = self.parse_s3_url(vehicles_s3_url)
                # Download the Parquet file
                self.s3_client.download_file(bucket_name, key, 'vehicles.parquet')
                # Load the Parquet file into a DataFrame
                vehicles_df = pd.read_parquet('vehicles.parquet')
                # Convert DataFrame to dictionary
                self.vehicles = vehicles_df.set_index('vehicle_id').to_dict(orient='index')
                print(f"Loaded {len(self.vehicles)} vehicles.")
                self.initialized = True
            else:
                print("No vehicles S3 link provided.")
                self.initialized = False
        except Exception as e:
            print(f"(AgentModule) Error loading initial state: {e}")
            self.initialized = False  # Ensure initialized remains False on error

    def parse_s3_url(self, s3_url):
        """Parse S3 URL to extract bucket name and key."""
        s3_url = s3_url.replace("s3://", "")
        bucket_name, key = s3_url.split('/', 1)
        return bucket_name, key

    def process_tick(self, tick_data):
        """Update vehicle positions based on the tick event and send updates to SimCore."""
        try:
            batch_updates = []
            for vehicle_id, vehicle in self.vehicles.items():
                # Update vehicle position
                current_position = vehicle.get('position', 0)
                speed = vehicle.get('speed', 20)
                # Simple movement logic
                new_position = current_position + speed * 0.01  # Adjust as needed
                vehicle['position'] = new_position
                # Prepare update message
                batch_updates.append({
                    'type': 'VehicleMoved',
                    'data': {
                        'vehicle_id': vehicle_id,
                        'road': vehicle.get('road', 'unknown'),
                        'position_on_road': new_position
                    }
                })

            # Send batch updates to SimCoreUpdates queue
            sqsUtility.send_batch_messages(self.queue_urls['SimCoreUpdates'], batch_updates)
            print(f"AgentModule sent updates to SimCore for tick {tick_data['tick_number']}")
        except Exception as e:
            print(f"(AgentModule) Error processing tick: {e}")

if __name__ == "__main__":
    print("Starting AgentModule...")

    agent_module = AgentModule()

    # Load initial state
    agent_module.load_initial_state()

    if agent_module.initialized:
        try:
            # Start processing messages
            while True:
                agent_module.process_messages()
                time.sleep(0.1)  # Small delay to prevent tight loop

        except KeyboardInterrupt:
            print("AgentModule stopped by user.")
        except Exception as e:
            print(f"Error in AgentModule: {e}")
        finally:
            print("AgentModule shutting down.")
    else:
        print("Failed to initialize AgentModule. Exiting.")
