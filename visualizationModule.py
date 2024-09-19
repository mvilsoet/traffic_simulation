import asyncio
import boto3
import json
from botocore.exceptions import ClientError
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from collections import deque

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

    async def initialize(self):
        # Get queue URLs
        queues = ['SimulationEvents', 'VehicleEvents.fifo', 'TrafficControlEvents.fifo']
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

            await asyncio.sleep(0.1)  # Short sleep to prevent tight looping

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

async def run_async_tasks(viz_module):
    await viz_module.initialize()
    await viz_module.process_messages()

def run_dash_app(viz_module):
    app = viz_module.create_dash_app()
    app.run_server(debug=True, use_reloader=False)

if __name__ == "__main__":
    print("Starting VisualizationModule...")
    viz_module = VisualizationModule()
    
    # Run the async task in a separate thread
    import threading
    thread = threading.Thread(target=lambda: asyncio.run(run_async_tasks(viz_module)))
    thread.start()
    print("Async tasks started in separate thread.")

    print("Starting Dash application...")
    try:
        # Run the Dash app in the main thread
        run_dash_app(viz_module)
    except KeyboardInterrupt:
        print("VisualizationModule stopped by user.")
    except Exception as e:
        print(f"Error in VisualizationModule: {e}")
    finally:
        print("VisualizationModule shutting down.")