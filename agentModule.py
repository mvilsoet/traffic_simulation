import boto3
import json
import random
from botocore.exceptions import ClientError

# Load configuration from config.json
with open('config.json', 'r') as config_file:
    CONFIG = json.load(config_file)
    QUEUES = CONFIG.get('AGENT_MOD_QUEUES', ['VehicleEvents.fifo', 'SimulationEvents'])  # SQS queue names
    MAX_NUMBER_OF_MESSAGES = CONFIG.get('MAX_NUMBER_OF_MESSAGES', 10)  # Max number of messages to receive from SQS
    WAIT_TIME_SECONDS = CONFIG.get('WAIT_TIME_SECONDS', 1)  # Wait time for receiving messages from SQS

class AgentModule:
    def __init__(self):
        self.vehicles = {}
        self.sqs = boto3.client('sqs')
        self.queue_urls = {}

    def initialize(self):
        # Get queue URLs from config
        for queue in QUEUES:
            try:
                response = self.sqs.get_queue_url(QueueName=queue)
                self.queue_urls[queue] = response['QueueUrl']
            except ClientError as e:
                print(f"Error getting queue URL for {queue}: {e}")

    def process_messages(self):
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_urls['SimulationEvents'],
                MaxNumberOfMessages=MAX_NUMBER_OF_MESSAGES,  # Use config for max messages
                WaitTimeSeconds=WAIT_TIME_SECONDS  # Use config for wait time
            )

            messages = response.get('Messages', [])
            for message in messages:
                event = json.loads(message['Body'])
                if event['type'] == 'SimulationTick':
                    self.process_tick(event['data'])

                # Delete the message from the queue
                self.sqs.delete_message(
                    QueueUrl=self.queue_urls['SimulationEvents'],
                    ReceiptHandle=message['ReceiptHandle']
                )
        except Exception as e:
            print(f"Error processing messages: {e}")

    def process_tick(self, tick_data):
        for vehicle_id, vehicle in self.vehicles.items():
            # Simple movement logic (replace with more complex behavior as needed)
            new_position = (
                vehicle['position'][0] + random.uniform(-3, 3),
                vehicle['position'][1] + random.uniform(-3, 3)
            )
            self.vehicles[vehicle_id]['position'] = new_position
            
            # Publish VehicleMoved event
            self.publish_event('VehicleMoved', {
                'vehicle_id': vehicle_id,
                'position': new_position
            })

    def publish_event(self, event_type, data):
        message_body = json.dumps({'type': event_type, 'data': data})
        try:
            self.sqs.send_message(
                QueueUrl=self.queue_urls['VehicleEvents.fifo'],
                MessageBody=message_body,
                MessageGroupId='vehicle_events'  # Required for FIFO queues
            )
        except ClientError as e:
            print(f"Error publishing {event_type} event: {e}")

    def create_vehicle(self, vehicle_id, initial_position):
        self.vehicles[vehicle_id] = {'position': initial_position}
        self.publish_event('VehicleCreated', {
            'vehicle_id': vehicle_id,
            'position': initial_position
        })

    def run(self):
        self.initialize()
        
        # Create some initial vehicles
        for i in range(10):
            self.create_vehicle(f"vehicle_{i}", (random.random() * 100, random.random() * 100))
        
        # Start processing messages
        while True:
            self.process_messages()

if __name__ == "__main__":
    print("Starting AgentModule...")
    agent_module = AgentModule()
    try:
        agent_module.run()
    except KeyboardInterrupt:
        print("AgentModule stopped by user.")
    except Exception as e:
        print(f"Error in AgentModule: {e}")
    finally:
        print("AgentModule shutting down.")
