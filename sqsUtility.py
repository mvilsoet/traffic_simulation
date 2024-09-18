import boto3
import json
import logging

# Set up logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration
try:
    with open('config.json', 'r') as config_file:
        CONFIG = json.load(config_file)
except FileNotFoundError:
    logging.error("config.json file not found")
    raise
except json.JSONDecodeError:
    logging.error("Error parsing config.json")
    raise

# AWS Configuration
AWS_REGION = CONFIG['aws']['region']
SQS_QUEUE_VEHICLE_UPDATES = CONFIG['sqs']['queue_vehicle_updates']
SQS_QUEUE_TRAFFIC_UPDATES = CONFIG['sqs']['queue_traffic_updates']

try:
    sqs_client = boto3.client('sqs', region_name=AWS_REGION)
    logging.info(f"SQS client created for region {AWS_REGION}")
except Exception as e:
    logging.error(f"Error creating SQS client: {str(e)}")
    raise

def get_queue_url(queue_name):
    try:
        logging.info(f"Attempting to get URL for queue: {queue_name}")
        response = sqs_client.get_queue_url(QueueName=queue_name)
        logging.info(f"Successfully retrieved URL for queue: {queue_name}")
        return response['QueueUrl']
    except sqs_client.exceptions.QueueDoesNotExist:
        logging.error(f"Queue does not exist: {queue_name}")
        raise
    except Exception as e:
        logging.error(f"Error getting queue URL for {queue_name}: {str(e)}")
        raise

def send_sqs_message(queue_name, message):
    try:
        queue_url = get_queue_url(queue_name)
        logging.info(f"Sending message to queue: {queue_name}")
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        logging.info(f"Message sent successfully to queue: {queue_name}")
        return response
    except Exception as e:
        logging.error(f"Error sending message to queue {queue_name}: {str(e)}")
        raise

def receive_sqs_messages(queue_name, max_messages=10, wait_time=20):
    try:
        queue_url = get_queue_url(queue_name)
        logging.info(f"Receiving messages from queue: {queue_name}")
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time
        )
        messages = response.get('Messages', [])
        logging.info(f"Received {len(messages)} messages from queue: {queue_name}")
        return messages
    except Exception as e:
        logging.error(f"Error receiving messages from queue {queue_name}: {str(e)}")
        raise

def delete_sqs_message(queue_name, receipt_handle):
    try:
        queue_url = get_queue_url(queue_name)
        logging.info(f"Deleting message from queue: {queue_name}")
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logging.info(f"Message deleted successfully from queue: {queue_name}")
    except Exception as e:
        logging.error(f"Error deleting message from queue {queue_name}: {str(e)}")
        raise

def process_sqs_messages(queue_name, callback):
    while True:
        try:
            messages = receive_sqs_messages(queue_name)
            for message in messages:
                body = json.loads(message['Body'])
                callback(body)
                delete_sqs_message(queue_name, message['ReceiptHandle'])
        except Exception as e:
            logging.error(f"Error processing messages from queue {queue_name}: {str(e)}")
            # You might want to add a sleep here to prevent tight looping in case of persistent errors
            # import time
            # time.sleep(5)

# Example usage and testing
if __name__ == "__main__":
    try:
        # Test sending a message
        send_sqs_message(SQS_QUEUE_VEHICLE_UPDATES, {
            'vehicle_id': 1,
            'position': 100,
            'road': 'R1'
        })

        # Test receiving and processing messages
        def print_message(message):
            print(f"Received message: {message}")
        
        process_sqs_messages(SQS_QUEUE_VEHICLE_UPDATES, print_message)
    except Exception as e:
        logging.error(f"An error occurred during testing: {str(e)}")
