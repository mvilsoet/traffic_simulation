import asyncio
import boto3
import json
from botocore.exceptions import ClientError
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from collections import deque
import threading

class VisualizationModule:
    def __init__(self):
        self.state = {
            'vehicles': {},
            'traffic_lights': {},
            'road_blockages': {}
        }
        self.sqs = boto3.client('sqs')
        self.queue_urls = {}
        self.update_queue = deque(maxlen=100)  # Store up to 100 updates
        self.running = True

    def initialize(self):
        # Get queue URLs
        queues = ['SimulationEvents', 'VehicleEvents.fifo', 'TrafficControlEvents.fifo']
        for queue in queues:
            try:
                response = self.sqs.get_queue_url(QueueName=queue)
                self.queue_urls[queue] = response['QueueUrl']
            except ClientError as e:
                print(f"Error getting queue URL for {queue}: {e}")

    def process_messages(self):
        while self.running:
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
                        self.update_queue.append(event)

                        # Delete the message from the queue
                        self.sqs.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
                except Exception as e:
                    print(f"Error processing messages from {queue_name}: {e}")

    def create_dash_app(self):
        app = dash.Dash(__name__)

        app.layout = html.Div([
            dcc.Graph(id='live-graph', animate=True),
            dcc.Interval(
                id='graph-update',
                interval=1000,  # in milliseconds
                n_intervals=0
            )
        ])

        @app.callback(
            Output('live-graph', 'figure'),
            Input('graph-update', 'n_intervals')
        )
        def update_graph(n):
            # Process all queued updates
            while self.update_queue:
                event = self.update_queue.popleft()
                self.process_event(event)

            # Create traces for vehicles, traffic lights, and road blockages
            vehicle_trace = go.Scatter(
                x=[v['position'][0] for v in self.state['vehicles'].values()],
                y=[v['position'][1] for v in self.state['vehicles'].values()],
                mode='markers',
                name='Vehicles',
                marker=dict(color='blue', size=10, symbol='circle')
            )

            traffic_light_trace = go.Scatter(
                x=[t['position'][0] for t in self.state['traffic_lights'].values()],
                y=[t['position'][1] for t in self.state['traffic_lights'].values()],
                mode='markers',
                name='Traffic Lights',
                marker=dict(
                    color=['green' if t['state'] == 'green' else 'red' for t in self.state['traffic_lights'].values()],
                    size=15,
                    symbol='square'
                )
            )

            road_blockage_trace = go.Scatter(
                x=[b['position'][0] for b in self.state['road_blockages'].values()],
                y=[b['position'][1] for b in self.state['road_blockages'].values()],
                mode='markers',
                name='Road Blockages',
                marker=dict(color='orange', size=12, symbol='triangle-up')
            )

            return {
                'data': [vehicle_trace, traffic_light_trace, road_blockage_trace],
                'layout': go.Layout(
                    xaxis=dict(range=[0, 100]),
                    yaxis=dict(range=[0, 100]),
                    title='Traffic Simulation'
                )
            }

        return app

    def process_event(self, event):
        event_type = event['type']
        data = event['data']

        if event_type == 'VehicleMoved' or event_type == 'VehicleCreated':
            self.state['vehicles'][data['vehicle_id']] = {'position': data['position']}
        elif event_type == 'TrafficLightChanged':
            self.state['traffic_lights'][data['light_id']] = {
                'state': data['state'],
                'position': self.state['traffic_lights'].get(data['light_id'], {}).get('position', (0, 0))
            }
        elif event_type == 'RoadBlockageCreated':
            self.state['road_blockages'][data['blockage_id']] = {'position': data['location']}
        elif event_type == 'RoadBlockageRemoved':
            self.state['road_blockages'].pop(data['blockage_id'], None)

    def run(self):
        self.initialize()
        
        # Start message processing in a separate thread
        message_thread = threading.Thread(target=self.process_messages)
        message_thread.start()

        # Create and run the Dash app in the main thread
        app = self.create_dash_app()
        app.run_server(debug=False, host='0.0.0.0', port=8050)

        # When the Dash app stops, stop the message processing
        self.running = False
        message_thread.join()

if __name__ == "__main__":
    print("Starting VisualizationModule...")
    viz_module = VisualizationModule()
    
    try:
        viz_module.run()
    except KeyboardInterrupt:
        print("VisualizationModule stopped by user.")
    except Exception as e:
        print(f"Error in VisualizationModule: {e}")
    finally:
        print("VisualizationModule shutting down.")