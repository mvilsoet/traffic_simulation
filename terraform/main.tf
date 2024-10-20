provider "aws" {
  region = "us-east-1"
}

# Create S3 Bucket for storing Parquet files
resource "aws_s3_bucket" "traffic_simulation_bucket" {
  bucket = "trafficsimulation"
  acl    = "private"
}

# Create SQS Standard Queue
resource "aws_sqs_queue" "standard_queue" {
  name = "SimulationEvents"
}

# Create SQS FIFO Queue
resource "aws_sqs_queue" "fifo_queue" {
  name                      = "SimCoreUpdates.fifo"
  fifo_queue                = true
  content_based_deduplication = true
}

# Create ECR Repositories for each service
resource "aws_ecr_repository" "simcore_repo" {
  name = "simcore"
}

resource "aws_ecr_repository" "agentmodule_repo" {
  name = "agentmodule"
}

resource "aws_ecr_repository" "trafficmodule_repo" {
  name = "trafficmodule"
}

resource "aws_ecr_repository" "vizmodule_repo" {
  name = "vizmodule"
}