# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY traffic_simulation/utils /app/utils
COPY traffic_simulation/core/ /app/

# Set the entry point
CMD ["python", "trafficModule.py"]
