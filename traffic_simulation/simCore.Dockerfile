FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire traffic_simulation folder into the container
COPY traffic_simulation /app/traffic_simulation

# Set the PYTHONPATH so Python knows where to find the traffic_simulation package
ENV PYTHONPATH="/app"

# Environment variables for AWS credentials (will be provided during runtime)
ENV AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
ENV AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY

# Set the entry point to start the simulation
CMD ["python", "traffic_simulation/core/simCore.py"]
