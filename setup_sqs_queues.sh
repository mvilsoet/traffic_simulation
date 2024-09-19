#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Setting up SQS queues for Traffic Simulation..."

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install it and try again."
    exit 1
fi

if ! aws configure list &> /dev/null; then
    echo "Error: AWS CLI is not configured. Please run 'aws configure' to set up your credentials."
    exit 1
fi

# Create SQS queues
aws sqs create-queue --queue-name SimulationEvents
aws sqs create-queue --queue-name VehicleEvents.fifo --attributes FifoQueue=true,ContentBasedDeduplication=true
aws sqs create-queue --queue-name TrafficControlEvents.fifo --attributes FifoQueue=true,ContentBasedDeduplication=true

echo "SQS queues created successfully."