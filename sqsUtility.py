import boto3
import json
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from the config.json file
with open('config.json', 'r') as config_file:
    CONFIG = json.load(config_file)
    AWS_REGION = CONFIG['aws']['region']
    SQS_QUEUE_VEHICLE_UPDATES = CONFIG['sqs']['queue_vehicle_updates']
    SQS_QUEUE_TRAFFIC_UPDATES = CONFIG['sqs']['queue_traffic_updates']
    MAX_NUMBER_OF_MESSAGES = CONFIG.get('sqs', {}).get('max_number_of_messages', 50)
    WAIT_TIME_SECONDS = CONFIG.get('sqs', {}).get('wait_time_seconds', 0)  

# AWS Configuration
try:
    sqs_client = boto3.client('sqs', region_name=AWS_REGION)
    logging.info(f"SQS client created for region {AWS_REGION}")
except Exception as e:
    logging.error(f"Error creating SQS client: {str(e)}")
    raise

# Dictionary to store queue URLs
queue_urls = {}

def get_queue_url(queue_name):
    """Retrieve and cache SQS queue URLs"""
    if queue_name not in queue_urls:
        try:
            response = sqs_client.get_queue_url(QueueName=queue_name)
            queue_urls[queue_name] = response['QueueUrl']
            logging.info(f"Retrieved and stored URL for queue: {queue_name}")
        except sqs_client.exceptions.QueueDoesNotExist:
            logging.error(f"Queue does not exist: {queue_name}")
            raise
        except Exception as e:
            logging.error(f"Error getting queue URL for {queue_name}: {str(e)}")
            raise
    return queue_urls[queue_name]

def send_sqs_message(queue_name, message):
    """Send a message to an SQS queue"""
    try:
        queue_url = get_queue_url(queue_name)
        message_body = json.dumps(message)
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body
        )
        logging.info(f"Message sent to queue {queue_name}: {message_body}")
        return response
    except Exception as e:
        logging.error(f"Error sending message to queue {queue_name}: {str(e)}")
        raise

def receive_sqs_messages(queue_name, max_number_of_messages=MAX_NUMBER_OF_MESSAGES, wait_time=WAIT_TIME_SECONDS):
    """Receive messages from an SQS queue"""
    try:
        queue_url = get_queue_url(queue_name)
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_number_of_messages,
            WaitTimeSeconds=wait_time
        )
        messages = response.get('Messages', [])
        logging.info(f"Received {len(messages)} messages from queue: {queue_name}")
        return messages
    except Exception as e:
        logging.error(f"Error receiving messages from queue {queue_name}: {str(e)}")
        raise

def delete_sqs_message(queue_name, receipt_handle):
    """Delete a message from an SQS queue"""
    try:
        queue_url = get_queue_url(queue_name)
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logging.info(f"Message deleted successfully from queue: {queue_name}")
    except Exception as e:
        logging.error(f"Error deleting message from queue {queue_name}: {str(e)}")
        raise

def process_sqs_messages(queue_name, callback, max_number_of_messages=MAX_NUMBER_OF_MESSAGES, wait_time=WAIT_TIME_SECONDS):
    """Process messages from an SQS queue and execute a callback function"""
    messages = receive_sqs_messages(queue_name, max_number_of_messages, wait_time)
    for message in messages:
        try:
            body = json.loads(message['Body'])
            callback(body)
            delete_sqs_message(queue_name, message['ReceiptHandle'])
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding message: {str(e)}")
            logging.error(f"Raw message content: {message['Body']}")
        except Exception as e:
            logging.error(f"Error processing message: {str(e)}")


if __name__ == "__main__":
    pass
