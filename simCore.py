import boto3
import json
import time
from botocore.exceptions import ClientError

class SimCore:
    def __init__(self):
        self.state = {
            'roads': {},
            'vehicles': {},
            'traffic_lights': {},
            'road_blockages': {}
        }
        self.sqs = boto3.client('sqs')
        self.queue_urls = {}

    def initialize(self):
        # Get queue URLs
        queues = ['VehicleEvents.fifo', 'TrafficControlEvents.fifo', 'SimulationEvents']
        for queue in queues:
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
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=1
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
                QueueUrl=self.queue_urls['SimulationEvents'],
                MessageBody=message_body
            )
        except ClientError as e:
            print(f"Error publishing {event_type} event: {e}")

    def run(self):
        self.initialize()
        while True:
            self.publish_event('SimulationTick', {'time': self.state.get('time', 0)})
            self.state['time'] = self.state.get('time', 0) + 1
            self.process_messages()
            time.sleep(1)  # Adjust tick rate as needed

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