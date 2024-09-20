import boto3
import json
import time
from botocore.exceptions import ClientError

class SimCore:
    def __init__(self):
        with open('config.json', 'r') as config_file:
            CONFIG = json.load(config_file)
            self.QUEUES = CONFIG['QUEUES']
            self.TICK_INTERVAL = CONFIG.get('TICK_INTERVAL', 0.1)  # Default to 0.1 seconds
            self.MAX_NUMBER_OF_MESSAGES = CONFIG.get('MAX_NUMBER_OF_MESSAGES', 10)  # Default to 10
            self.WAIT_TIME_SECONDS = CONFIG.get('WAIT_TIME_SECONDS', 1)  # Default to 1 second
            self.SIMCORE_QUEUE = CONFIG.get('SIMCORE_QUEUE', 'SimulationEvents')  # Default to SimulationEvents Queue
    
        # Simulation state
        self.state = {
            'roads': {},
            'vehicles': {},
            'traffic_lights': {},
            'road_blockages': {}
        }

        # Initialize SQS client
        self.sqs = boto3.client('sqs')
        self.queue_urls = {}

    def initialize(self):
        # Get queue URLs from the config file
        for queue in self.QUEUES:
            try:
                response = self.sqs.get_queue_url(QueueName=queue)
                self.queue_urls[queue] = response['QueueUrl']
            except ClientError as e:
                print(f"Error getting queue URL for {queue}: {e}")

    def process_messages(self):
        for queue_name, queue_url in self.queue_urls.items():
            try:
                response = self.sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=self.MAX_NUMBER_OF_MESSAGES,  # Use value from config
                    WaitTimeSeconds=self.WAIT_TIME_SECONDS  # Use value from config
                )

                messages = response.get('Messages', [])
                for message in messages:
                    event = json.loads(message['Body'])
                    self.process_event(event)

                    # Delete the message from the queue
                    self.sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
            except Exception as e:
                print(f"Error processing messages from {queue_name}: {e}")

    def process_event(self, event):
        event_type = event['type']

        if event_type == 'VehicleMoved':
            self.state['vehicles'][event['data']['vehicle_id']] = event['data']['position']
        elif event_type == 'TrafficLightChanged':
            self.state['traffic_lights'][event['data']['light_id']] = event['data']['state']
        elif event_type == 'RoadBlockageCreated':
            self.state['road_blockages'][event['data']['blockage_id']] = event['data']['location']
        elif event_type == 'RoadBlockageRemoved':
            self.state['road_blockages'].pop(event['data']['blockage_id'], None)

        # Publish StateChanged event
        self.publish_event('StateChanged', self.state)

    def publish_event(self, event_type, data):
        message_body = json.dumps({'type': event_type, 'data': data})
        try:
            self.sqs.send_message(
                QueueUrl=self.queue_urls[self.SIMCORE_QUEUE],
                MessageBody=message_body
            )
        except ClientError as e:
            print(f"Error publishing {event_type} event: {e}")

    def run(self):
        self.initialize()
        while True:
            self.publish_event('SimulationTick', {'time': self.state.get('time', 0)})
            self.state['time'] = self.state.get('time', 0) + 1
            print("tick: ", self.state['time'])
            self.process_messages()
            time.sleep(self.TICK_INTERVAL)  # Use tick interval from config

if __name__ == "__main__":
    print("Starting SimCore...")
    sim_core = SimCore()
    try:
        sim_core.run()
    except KeyboardInterrupt:
        print("Simulation stopped by user.")
    except Exception as e:
        print(f"Error in SimCore: {e}")
    finally:
        print("SimCore shutting down.")
