import json
from sqsUtility import send_sqs_message, process_sqs_messages

# Load configuration
with open('config.json', 'r') as config_file:
    CONFIG = json.load(config_file)

# Parameters from config
DEFAULT_TRAFFIC_LIGHT_CYCLE = CONFIG['traffic_light']['default_cycle']
DEFAULT_ROAD_BLOCKAGE_DURATION = CONFIG['road_blockage']['default_duration']
INITIAL_INTERSECTION = CONFIG['traffic_light']['initial_intersection']
INITIAL_BLOCKED_ROAD = CONFIG['road_blockage']['initial_blocked_road']
SQS_QUEUE_VEHICLE_UPDATES = CONFIG['sqs']['queue_vehicle_updates']
SQS_QUEUE_TRAFFIC_UPDATES = CONFIG['sqs']['queue_traffic_updates']

class TrafficLight:
    def __init__(self, intersection_id, cycle_duration=DEFAULT_TRAFFIC_LIGHT_CYCLE):
        self.intersection_id = intersection_id
        self.cycle_duration = cycle_duration
        self.current_state = "Green"
        self.time_in_state = 0

    def update(self):
        self.time_in_state += 1
        if self.time_in_state >= self.cycle_duration:
            self.time_in_state = 0
            self.current_state = "Green" if self.current_state == "Red" else "Red"
        return {
            'type': 'traffic_light_update',
            'intersection_id': self.intersection_id,
            'state': self.current_state
        }

class RoadBlockage:
    def __init__(self, road_id, duration):
        self.road_id = road_id
        self.duration = duration
        self.time_active = 0

    def update(self):
        self.time_active += 1
        is_active = self.time_active < self.duration
        return {
            'type': 'road_blockage_update',
            'road_id': self.road_id,
            'is_blocked': is_active
        }

class TrafficControlSystem:
    def __init__(self):
        self.traffic_lights = {}
        self.road_blockages = []

    def add_traffic_light(self, intersection_id, cycle_duration=DEFAULT_TRAFFIC_LIGHT_CYCLE):
        traffic_light = TrafficLight(intersection_id, cycle_duration)
        self.traffic_lights[intersection_id] = traffic_light

    def create_road_blockage(self, road_id, duration=DEFAULT_ROAD_BLOCKAGE_DURATION):
        blockage = RoadBlockage(road_id, duration)
        self.road_blockages.append(blockage)

    def update_all(self):
        for light in self.traffic_lights.values():
            update = light.update()
            send_sqs_message(SQS_QUEUE_TRAFFIC_UPDATES, update)

        for blockage in self.road_blockages[:]:
            update = blockage.update()
            send_sqs_message(SQS_QUEUE_TRAFFIC_UPDATES, update)
            if not update['is_blocked']:
                self.road_blockages.remove(blockage)

        def process_message(message):
            if message['type'] == 'create_road_blockage':
                self.create_road_blockage(message['road_id'], message['duration'])

        process_sqs_messages(SQS_QUEUE_TRAFFIC_UPDATES, process_message)

if __name__ == "__main__":
    traffic_system = TrafficControlSystem()
    traffic_system.add_traffic_light(INITIAL_INTERSECTION)
    traffic_system.create_road_blockage(INITIAL_BLOCKED_ROAD)

    while True:
        traffic_system.update_all()
