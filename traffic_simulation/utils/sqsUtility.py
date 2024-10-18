import os
import boto3
import json
import logging
import uuid

# Set up logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from config.json
config_file = os.path.join(os.path.dirname(__file__), '..', 'core', 'config.json')  # relative path D:
with open(config_file, 'r') as config_file:
    CONFIG = json.load(config_file)
    AWS_REGION = CONFIG['aws']['region']
    MAX_NUMBER_OF_MESSAGES = CONFIG.get('MAX_NUMBER_OF_MESSAGES', 10)
    WAIT_TIME_SECONDS = CONFIG.get('WAIT_TIME_SECONDS', 1)

# AWS Configuration
try:
    sqs_client = boto3.client('sqs', region_name=AWS_REGION)
    logging.info(f"SQS client created for region {AWS_REGION}")
except Exception as e:
    logging.error(f"Error creating SQS client: {str(e)}")
    raise

# Dictionary to store queue URLs
queue_urls_cache = {}

def get_queue_urls(queue_names):
    """
    Retrieve and cache SQS queue URLs for a list of queue names.
    Returns a dictionary mapping queue names to queue URLs.
    """
    urls = {}
    for queue_name in queue_names:
        if queue_name in queue_urls_cache:
            urls[queue_name] = queue_urls_cache[queue_name]
        else:
            try:
                response = sqs_client.get_queue_url(QueueName=queue_name)
                queue_url = response['QueueUrl']
                queue_urls_cache[queue_name] = queue_url
                urls[queue_name] = queue_url
                logging.info(f"Retrieved and stored URL for queue: {queue_name}")
            except sqs_client.exceptions.QueueDoesNotExist:
                logging.error(f"Queue does not exist: {queue_name}")
                raise
            except Exception as e:
                logging.error(f"Error getting queue URL for {queue_name}: {str(e)}")
                raise
    return urls

def send_message(queue_url, message, message_group_id=None):
    """
    Send a message to an SQS queue.
    If the queue is a FIFO queue and a message_group_id is provided,
    MessageGroupId and MessageDeduplicationId will be included.
    """
    try:
        message_body = json.dumps(message)
        params = {
            'QueueUrl': queue_url,
            'MessageBody': message_body
        }
        if 'fifo' in queue_url.lower() and message_group_id:
            params['MessageGroupId'] = message_group_id
            params['MessageDeduplicationId'] = str(uuid.uuid4())

        response = sqs_client.send_message(**params)
        logging.info(f"Message sent to queue {queue_url}: {message_body}")
        return response
    except Exception as e:
        logging.error(f"Error sending message to queue {queue_url}: {str(e)}")
        raise

def send_batch_messages(queue_url, messages, message_group_id=None):
    """
    Send a batch of messages to an SQS queue.
    Handles FIFO queues by including MessageGroupId and MessageDeduplicationId.
    """
    entries = []
    for i, message in enumerate(messages):
        entry = {
            'Id': str(i),
            'MessageBody': json.dumps(message)
        }
        if 'fifo' in queue_url.lower() and message_group_id:
            entry['MessageGroupId'] = message_group_id
            entry['MessageDeduplicationId'] = str(uuid.uuid4())
        entries.append(entry)

    # SQS batch messages have a limit of 10 messages per batch
    responses = []
    for i in range(0, len(entries), 10):
        batch_entries = entries[i:i+10]
        try:
            response = sqs_client.send_message_batch(
                QueueUrl=queue_url,
                Entries=batch_entries
            )
            responses.append(response)
            logging.info(f"Batch messages sent to queue {queue_url}: {len(batch_entries)} messages")
        except Exception as e:
            logging.error(f"Error sending batch messages to queue {queue_url}: {str(e)}")
            raise
    return responses

def receive_messages(queue_url, max_number_of_messages=MAX_NUMBER_OF_MESSAGES, wait_time_seconds=WAIT_TIME_SECONDS):
    """
    Receive messages from an SQS queue.
    Returns a list of messages.
    """
    try:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_number_of_messages,
            WaitTimeSeconds=wait_time_seconds,
            VisibilityTimeout=10,  # Adjust as needed
            MessageAttributeNames=['All']
        )
        messages = response.get('Messages', [])
        logging.info(f"Received {len(messages)} messages from queue: {queue_url}")
        return messages
    except Exception as e:
        logging.error(f"Error receiving messages from queue {queue_url}: {str(e)}")
        raise

def delete_message(queue_url, receipt_handle):
    """
    Delete a message from an SQS queue using the receipt handle.
    """
    try:
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logging.info(f"Message deleted successfully from queue: {queue_url}")
    except Exception as e:
        logging.error(f"Error deleting message from queue {queue_url}: {str(e)}")
        raise

if __name__ == "__main__":
    pass  # This utility module is intended to be imported and used by other modules.
