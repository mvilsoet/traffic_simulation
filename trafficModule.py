import asyncio
import boto3
import json
import random
from botocore.exceptions import ClientError

class TrafficControlModule:
    def __init__(self):
        self.traffic_lights = {}
        self.road_blockages = {}
        self.sqs = boto3.client('sqs')
        self.queue_urls = {}

    async def initialize(self):
        # Get queue URLs
        queues = ['TrafficControlEvents.fifo', 'SimulationEvents']
        for queue in queues:
            try:
                response = self.sqs.get_queue_url(QueueName=queue)
                self.queue_urls[queue] = response['QueueUrl']
            except ClientError as e:
                print(f"Error getting queue URL for {queue}: {e}")

    async def process_messages(self):
        while True:
            try:
                response = self.sqs.receive_message(
                    QueueUrl=self.queue_urls['SimulationEvents'],
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=20
                )

                messages = response.get('Messages', [])
                for message in messages:
                    event = json.loads(message['Body'])
                    if event['type'] == 'SimulationTick':
                        await self.process_tick(event['data'])

                    # Delete the message from the queue
                    self.sqs.delete_message(
                        QueueUrl=self.queue_urls['SimulationEvents'],
                        ReceiptHandle=message['ReceiptHandle']
                    )
            except Exception as e:
                print(f"Error processing messages: {e}")

            await asyncio.sleep(0.1)  # Short sleep to prevent tight looping

    async def process_tick(self, tick_data):
        # Update traffic lights
        for light_id, light in self.traffic_lights.items():
            if random.random() < 0.1:  # 10% chance to change light
                new_state = 'green' if light['state'] == 'red' else 'red'
                self.traffic_lights[light_id]['state'] = new_state
                await self.publish_event('TrafficLightChanged', {
                    'light_id': light_id,
                    'state': new_state
                })

        # Update road blockages
        for blockage_id, blockage in list(self.road_blockages.items()):
            blockage['duration'] -= 1
            if blockage['duration'] <= 0:
                del self.road_blockages[blockage_id]
                await self.publish_event('RoadBlockageRemoved', {
                    'blockage_id': blockage_id
                })

        # Randomly create new road blockages
        if random.random() < 0.05:  # 5% chance to create a new blockage
            blockage_id = f"blockage_{len(self.road_blockages)}"
            self.road_blockages[blockage_id] = {
                'location': (random.random() * 100, random.random() * 100),
                'duration': random.randint(10, 50)
            }
            await self.publish_event('RoadBlockageCreated', {
                'blockage_id': blockage_id,
                'location': self.road_blockages[blockage_id]['location']
            })

    async def publish_event(self, event_type, data):
        message_body = json.dumps({'type': event_type, 'data': data})
        try:
            self.sqs.send_message(
                QueueUrl=self.queue_urls['TrafficControlEvents.fifo'],
                MessageBody=message_body,
                MessageGroupId='traffic_control_events'  # Required for FIFO queues
            )
        except ClientError as e:
            print(f"Error publishing {event_type} event: {e}")

    async def create_traffic_light(self, light_id, initial_state):
        self.traffic_lights[light_id] = {'state': initial_state}
        await self.publish_event('TrafficLightChanged', {
            'light_id': light_id,
            'state': initial_state
        })

async def main():
    traffic_control = TrafficControlModule()
    await traffic_control.initialize()
    
    # Create some initial traffic lights
    for i in range(5):
        await traffic_control.create_traffic_light(f"light_{i}", random.choice(['red', 'green']))
    
    # Start processing messages
    await traffic_control.process_messages()

if __name__ == "__main__":
    asyncio.run(main())