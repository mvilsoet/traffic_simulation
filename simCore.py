import asyncio
import boto3
import json
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

    async def initialize(self):
        # Get queue URLs
        queues = ['VehicleEvents.fifo', 'TrafficControlEvents.fifo', 'SimulationEvents']
        for queue in queues:
            try:
                response = self.sqs.get_queue_url(QueueName=queue)
                self.queue_urls[queue] = response['QueueUrl']
            except ClientError as e:
                print(f"Error getting queue URL for {queue}: {e}")

    async def process_messages(self):
        while True:
            for queue_name, queue_url in self.queue_urls.items():
                try:
                    response = self.sqs.receive_message(
                        QueueUrl=queue_url,
                        MaxNumberOfMessages=10,
                        WaitTimeSeconds=20
                    )

                    messages = response.get('Messages', [])
                    for message in messages:
                        event = json.loads(message['Body'])
                        await self.process_event(event)

                        # Delete the message from the queue
                        self.sqs.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                except Exception as e:
                    print(f"Error processing messages from {queue_name}: {e}")

            await asyncio.sleep(0.1)  # Short sleep to prevent tight looping

    async def process_event(self, event):
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
        await self.publish_event('StateChanged', self.state)

    async def publish_event(self, event_type, data):
        message_body = json.dumps({'type': event_type, 'data': data})
        try:
            self.sqs.send_message(
                QueueUrl=self.queue_urls['SimulationEvents'],
                MessageBody=message_body
            )
        except ClientError as e:
            print(f"Error publishing {event_type} event: {e}")

    async def run(self):
        while True:
            await self.publish_event('SimulationTick', {'time': self.state.get('time', 0)})
            self.state['time'] = self.state.get('time', 0) + 1
            await asyncio.sleep(1)  # Adjust tick rate as needed

async def main():
    sim_core = SimCore()
    await sim_core.initialize()
    await asyncio.gather(sim_core.run(), sim_core.process_messages())

if __name__ == "__main__":
    asyncio.run(main())