# Store tf.state in S3
terraform {
  backend "s3" {
    bucket = "mvilsoet-bucket"
    key    = "terraform.tfstate"
    region = "us-east-2"
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Create S3 Bucket for traffic simulation data
resource "aws_s3_bucket" "traffic_simulation_bucket" {
  bucket = "trafficsimulation"
}

resource "aws_s3_bucket_ownership_controls" "traffic_simulation_bucket_ownership" {
  bucket = aws_s3_bucket.traffic_simulation_bucket.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "traffic_simulation_bucket_acl" {
  depends_on = [aws_s3_bucket_ownership_controls.traffic_simulation_bucket_ownership]

  bucket = aws_s3_bucket.traffic_simulation_bucket.id
  acl    = "private"
}

# Create SQS Standard Queue
resource "aws_sqs_queue" "standard_queue" {
  name = "SimulationEvents"
}

# Create SQS FIFO Queue
resource "aws_sqs_queue" "fifo_queue" {
  name                        = "SimCoreUpdates.fifo"
  fifo_queue                  = true
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