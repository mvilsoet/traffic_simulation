import boto3
import json
import random
from botocore.exceptions import ClientError

# Load configuration from config.json
with open('config.json', 'r') as config_file:
    CONFIG = json.load(config_file)
    QUEUES = CONFIG.get('TRAFFIC_MOD_QUEUES', ['TrafficControlEvents.fifo', 'SimulationEvents'])  # List of SQS queues to use
    MAX_NUMBER_OF_MESSAGES = CONFIG.get('MAX_NUMBER_OF_MESSAGES', 100)  # Max number of messages to receive from SQS
    WAIT_TIME_SECONDS = CONFIG.get('WAIT_TIME_SECONDS', 0)  # SQS message wait time
    TRAFFIC_LIGHT_CHANGE_PROBABILITY = CONFIG.get('TRAFFIC_LIGHT_CHANGE_PROBABILITY', 0.1)  # Probability of changing a traffic light state per tick
    ROAD_BLOCKAGE_CREATION_PROBABILITY = CONFIG.get('ROAD_BLOCKAGE_CREATION_PROBABILITY', 0.3)  # Probability of creating a new road blockage
    BLOCKAGE_DURATION_RANGE = CONFIG.get('BLOCKAGE_DURATION_RANGE', [10, 50])  # Range of duration for road blockages

class TrafficControlModule:
    def __init__(self):
        self.traffic_lights = {}
        self.road_blockages = {}
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
                MaxNumberOfMessages=MAX_NUMBER_OF_MESSAGES,  # Use configured max messages
                WaitTimeSeconds=WAIT_TIME_SECONDS  # Use configured wait time
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
        # Update traffic lights
        for light_id, light in self.traffic_lights.items():
            if random.random() < TRAFFIC_LIGHT_CHANGE_PROBABILITY:  # Use configured probability
                new_state = 'green' if light['state'] == 'red' else 'red'
                self.traffic_lights[light_id]['state'] = new_state
                self.publish_event('TrafficLightChanged', {
                    'light_id': light_id,
                    'state': new_state
                })

        # Update road blockages
        for blockage_id, blockage in list(self.road_blockages.items()):
            blockage['duration'] -= 1
            if blockage['duration'] <= 0:
                del self.road_blockages[blockage_id]
                self.publish_event('RoadBlockageRemoved', {
                    'blockage_id': blockage_id
                })

        # Randomly create new road blockages
        if random.random() < ROAD_BLOCKAGE_CREATION_PROBABILITY:  # Use configured probability
            blockage_id = f"blockage_{len(self.road_blockages)}"
            self.road_blockages[blockage_id] = {
                'location': (random.random() * 100, random.random() * 100),
                'duration': random.randint(*BLOCKAGE_DURATION_RANGE)  # Use configured range
            }
            self.publish_event('RoadBlockageCreated', {
                'blockage_id': blockage_id,
                'location': self.road_blockages[blockage_id]['location']
            })

    def publish_event(self, event_type, data):
        message_body = json.dumps({'type': event_type, 'data': data})
        try:
            self.sqs.send_message(
                QueueUrl=self.queue_urls['TrafficControlEvents.fifo'],
                MessageBody=message_body,
                MessageGroupId='traffic_control_events'  # Required for FIFO queues
            )
        except ClientError as e:
            print(f"Error publishing {event_type} event: {e}")

    def create_traffic_light(self, light_id, initial_state):
        self.traffic_lights[light_id] = {'state': initial_state}
        self.publish_event('TrafficLightChanged', {
            'light_id': light_id,
            'state': initial_state
        })

    def run(self):
        self.initialize()
        
        # Create some initial traffic lights
        for i in range(5):
            self.create_traffic_light(f"light_{i}", random.choice(['red', 'green']))
        
        # Start processing messages
        while True:
            self.process_messages()

if __name__ == "__main__":
    print("Starting TrafficControlModule...")
    traffic_control = TrafficControlModule()
    try:
        traffic_control.run()
    except KeyboardInterrupt:
        print("TrafficControlModule stopped by user.")
    except Exception as e:
        print(f"Error in TrafficControlModule: {e}")
    finally:
        print("TrafficControlModule shutting down.")
