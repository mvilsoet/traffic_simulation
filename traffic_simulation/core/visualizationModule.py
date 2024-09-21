# visualization.py

import json
import time
import threading
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

# Global variable to store simulation state
simulation_state = {
    'vehicles': {},
    'traffic_lights': {},
    'road_blockages': {},
    'intersections': {},
    'roads': {}
}

# Function to continuously read the simulation state file
def update_simulation_state():
    while True:
        try:
            with open('sim_state.json', 'r') as f:
                state = json.load(f)
                simulation_state.update(state)
        except FileNotFoundError:
            pass  # The file might not exist yet
        except json.JSONDecodeError:
            pass  # The file might be incomplete
        time.sleep(1)  # Adjust the frequency as needed

# Start the state updater in a separate thread
state_updater_thread = threading.Thread(target=update_simulation_state, daemon=True)
state_updater_thread.start()

# Initialize the Dash app
app = dash.Dash(__name__)
app.title = 'Traffic Simulation Visualization'

# Define the layout
app.layout = html.Div(children=[
    html.H1(children='Traffic Simulation Visualization'),
    dcc.Graph(id='simulation-graph'),
    dcc.Interval(
        id='interval-component',
        interval=1*1000,  # Update every 1 second
        n_intervals=0
    )
])

# Callback to update the graph
@app.callback(
    Output('simulation-graph', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_graph(n):
    # Create data frames from the simulation state
    vehicles = simulation_state['vehicles']
    traffic_lights = simulation_state['traffic_lights']
    road_blockages = simulation_state['road_blockages']
    intersections = simulation_state['intersections']
    roads = simulation_state['roads']

    # Prepare data for plotting
    vehicle_df = pd.DataFrame.from_dict(vehicles, orient='index').reset_index()
    vehicle_df.rename(columns={'index': 'vehicle_id'}, inplace=True)

    # For simplicity, we'll plot vehicles on a scatter plot
    # Assume positions are along the x-axis for demonstration purposes
    if not vehicle_df.empty:
        fig = px.scatter(vehicle_df, x='position', y=[0]*len(vehicle_df), color='road',
                         hover_name='vehicle_id', title='Vehicle Positions')
    else:
        fig = px.scatter(title='No Vehicle Data Available')

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
