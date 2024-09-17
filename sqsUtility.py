import boto3
import json

# Load configuration
with open('config.json', 'r') as config_file:
    CONFIG = json.load(config_file)

# AWS Configuration
AWS_REGION = CONFIG['aws']['region']
SQS_QUEUE_VEHICLE_UPDATES = CONFIG['sqs']['queue_vehicle_updates']
SQS_QUEUE_TRAFFIC_UPDATES = CONFIG['sqs']['queue_traffic_updates']

sqs_client = boto3.client('sqs', region_name=AWS_REGION)

def get_queue_url(queue_name):
    response = sqs_client.get_queue_url(QueueName=queue_name)
    return response['QueueUrl']

def send_sqs_message(queue_name, message):
    queue_url = get_queue_url(queue_name)
    response = sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )
    return response

def receive_sqs_messages(queue_name, max_messages=10, wait_time=20):
    queue_url = get_queue_url(queue_name)
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=wait_time
    )
    messages = response.get('Messages', [])
    return messages

def delete_sqs_message(queue_name, receipt_handle):
    queue_url = get_queue_url(queue_name)
    sqs_client.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )

def process_sqs_messages(queue_name, callback):
    while True:
        messages = receive_sqs_messages(queue_name)
        for message in messages:
            body = json.loads(message['Body'])
            callback(body)
            delete_sqs_message(queue_name, message['ReceiptHandle'])

# Example usage
if __name__ == "__main__":
    try:
        # Sender example
        send_sqs_message(SQS_QUEUE_VEHICLE_UPDATES, {
            'vehicle_id': 1,
            'position': 100,
            'road': 'R1'
        })

        # Receiver example
        def print_message(message):
            print(f"Received message: {message}")
        
        process_sqs_messages(SQS_QUEUE_VEHICLE_UPDATES, print_message)
    except Exception as e:
        print(f"An error occurred: {e}")