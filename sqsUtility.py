import boto3
import json
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

# Dictionary to store queue URLs
queue_urls = {}

def get_queue_url(queue_name):
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
    try:
        queue_url = get_queue_url(queue_name)
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
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logging.info(f"Message deleted successfully from queue: {queue_name}")
    except Exception as e:
        logging.error(f"Error deleting message from queue {queue_name}: {str(e)}")
        raise

def process_sqs_messages(queue_name, callback, max_messages=10, wait_time=20):
    messages = receive_sqs_messages(queue_name, max_messages, wait_time)
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
    # print("Testing SQS Utility...")
    # try:
    #     # Test queue URL retrieval
    #     test_queue_name = SQS_QUEUE_VEHICLE_UPDATES
    #     queue_url = get_queue_url(test_queue_name)
    #     print(f"Successfully retrieved URL for queue: {test_queue_name}")

    #     # Test message sending
    #     test_message = {"type": "test", "data": {"message": "This is a test"}}
    #     response = send_sqs_message(test_queue_name, test_message)
    #     print(f"Test message sent. MessageId: {response['MessageId']}")

    #     # Test message receiving and deletion
    #     messages = receive_sqs_messages(test_queue_name, max_messages=1, wait_time=5)
    #     if messages:
    #         print(f"Received test message: {messages[0]['Body']}")
    #         delete_sqs_message(test_queue_name, messages[0]['ReceiptHandle'])
    #         print("Test message deleted from queue.")
    #     else:
    #         print("No messages received. This is expected if the queue was empty.")

    #     print("SQS Utility test completed successfully.")
    # except Exception as e:
    #     print(f"Error during SQS Utility test: {str(e)}")
    pass