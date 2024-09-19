import time
import json
from sqsUtility import send_sqs_message, process_sqs_messages

# Load configuration
with open('config.json', 'r') as config_file:
    CONFIG = json.load(config_file)

# Parameters from config
SIMULATION_STEP = CONFIG['simulation']['step']
DEFAULT_SIMULATION_DURATION = CONFIG['simulation']['duration']
SQS_QUEUE_VEHICLE_UPDATES = CONFIG['sqs']['queue_vehicle_updates']
SQS_QUEUE_TRAFFIC_UPDATES = CONFIG['sqs']['queue_traffic_updates']
GRID_WIDTH = CONFIG['visualization']['grid_width']
GRID_HEIGHT = CONFIG['visualization']['grid_height']

class SimulationCore:
    def __init__(self):
        self.clock = 0
        self.road_network = {}
        self.initialize_grid_roads()

    def initialize_grid_roads(self):
        # Create a grid of roads
        for i in range(GRID_WIDTH):
            for j in range(GRID_HEIGHT):
                if i < GRID_WIDTH - 1:
                    self.add_road(f"H{i}-{j}", (i, j), (i+1, j), 60)
                if j < GRID_HEIGHT - 1:
                    self.add_road(f"V{i}-{j}", (i, j), (i, j+1), 60)

    def add_road(self, road_id, start_node, end_node, speed_limit):
        self.road_network[road_id] = {
            'start': start_node,
            'end': end_node,
            'speed_limit': speed_limit
        }

    def update(self):
        self.clock += 1

        def process_message(message):
            if message['type'] == 'road_info_request':
                road_info = self.get_road_info(message['road_id'])
                response = {
                    'type': 'road_info_response',
                    'road_id': message['road_id'],
                    'road_info': road_info
                }
                send_sqs_message(SQS_QUEUE_TRAFFIC_UPDATES, response)
            elif 'vehicle_id' in message:
                print(f"Vehicle {message['vehicle_id']} update: Road {message['current_road']}, Position {message['position']}")

        process_sqs_messages(SQS_QUEUE_VEHICLE_UPDATES, process_message)

    def run(self, duration=DEFAULT_SIMULATION_DURATION):
        # Send initial road network information
        self.send_road_network()

        start_time = time.time()
        while time.time() - start_time < duration:
            self.update()
            time.sleep(SIMULATION_STEP)

    def get_road_info(self, road_id):
        road_info = self.road_network.get(road_id, {})
        road_info['available_roads'] = list(self.road_network.keys())
        return road_info

    def send_road_network(self):
        message = {
            'type': 'road_network_update',
            'roads': self.road_network
        }
        send_sqs_message(SQS_QUEUE_TRAFFIC_UPDATES, message)

if __name__ == "__main__":
    sim = SimulationCore()
    sim.run()
