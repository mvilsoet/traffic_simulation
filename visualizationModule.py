import json
import time
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from sqsUtility import process_sqs_messages
from threading import Thread
import queue

# Load configuration
with open('config.json', 'r') as config_file:
    CONFIG = json.load(config_file)

GRID_WIDTH = CONFIG['visualization']['grid_width']
GRID_HEIGHT = CONFIG['visualization']['grid_height']
SQS_QUEUE_VEHICLE_UPDATES = CONFIG['sqs']['queue_vehicle_updates']
SQS_QUEUE_TRAFFIC_UPDATES = CONFIG['sqs']['queue_traffic_updates']

class VisualizationModule:
    def __init__(self):
        self.vehicles = {}
        self.traffic_lights = {}
        self.road_blockages = {}
        self.update_queue = queue.Queue()

    def update_vehicle(self, vehicle_data):
        vehicle_id = vehicle_data['vehicle_id']
        x, y = vehicle_data['x'], vehicle_data['y']
        self.vehicles[vehicle_id] = (x, y)

    def update_traffic_light(self, traffic_light_data):
        intersection_id = traffic_light_data['intersection_id']
        state = traffic_light_data['state']
        x, y = divmod(hash(intersection_id), GRID_WIDTH)
        self.traffic_lights[intersection_id] = (x % GRID_WIDTH, y % GRID_HEIGHT, state)

    def update_road_blockage(self, blockage_data):
        road_id = blockage_data['road_id']
        is_blocked = blockage_data['is_blocked']
        if is_blocked:
            x, y = divmod(hash(road_id), GRID_WIDTH)
            self.road_blockages[road_id] = (x % GRID_WIDTH, y % GRID_HEIGHT)
        elif road_id in self.road_blockages:
            del self.road_blockages[road_id]

    def process_messages(self):
        def process_vehicle_message(message):
            if 'vehicle_id' in message:
                self.update_queue.put(('vehicle', message))

        def process_traffic_message(message):
            if message['type'] == 'traffic_light_update':
                self.update_queue.put(('traffic_light', message))
            elif message['type'] == 'road_blockage_update':
                self.update_queue.put(('road_blockage', message))

        while True:
            process_sqs_messages(SQS_QUEUE_VEHICLE_UPDATES, process_vehicle_message)
            process_sqs_messages(SQS_QUEUE_TRAFFIC_UPDATES, process_traffic_message)

    def run(self):
        app = dash.Dash(__name__)

        app.layout = html.Div([
            html.H1('Traffic Simulation Dashboard'),
            dcc.Graph(id='live-graph', animate=True),
            dcc.Interval(
                id='graph-update',
                interval=1000,  # in milliseconds
                n_intervals=0
            )
        ])

        @app.callback(Output('live-graph', 'figure'),
                      Input('graph-update', 'n_intervals'))
        def update_graph_scatter(n):
            while not self.update_queue.empty():
                update_type, data = self.update_queue.get()
                if update_type == 'vehicle':
                    self.update_vehicle(data)
                elif update_type == 'traffic_light':
                    self.update_traffic_light(data)
                elif update_type == 'road_blockage':
                    self.update_road_blockage(data)

            vehicle_trace = go.Scatter(
                x=[x for x, y in self.vehicles.values()],
                y=[y for x, y in self.vehicles.values()],
                mode='markers',
                name='Vehicles',
                marker=dict(color='blue', size=10)
            )

            traffic_light_trace = go.Scatter(
                x=[x for x, y, state in self.traffic_lights.values()],
                y=[y for x, y, state in self.traffic_lights.values()],
                mode='markers',
                name='Traffic Lights',
                marker=dict(
                    color=['green' if state == 'Green' else 'red' for _, _, state in self.traffic_lights.values()],
                    size=15,
                    symbol='circle-dot'
                )
            )

            road_blockage_trace = go.Scatter(
                x=[x for x, y in self.road_blockages.values()],
                y=[y for x, y in self.road_blockages.values()],
                mode='markers',
                name='Road Blockages',
                marker=dict(color='red', size=12, symbol='x')
            )

            return {
                'data': [vehicle_trace, traffic_light_trace, road_blockage_trace],
                'layout': go.Layout(
                    xaxis=dict(range=[0, GRID_WIDTH]),
                    yaxis=dict(range=[0, GRID_HEIGHT]),
                    title='Traffic Simulation'
                )
            }

        # Start the message processing in a separate thread
        Thread(target=self.process_messages, daemon=True).start()

        # Run the Dash app
        app.run_server(debug=True, host='0.0.0.0', port=8050)

if __name__ == "__main__":
    viz = VisualizationModule()
    viz.run()
