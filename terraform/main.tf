# Cost estimate
module "pricing" {
  source  = "terraform-aws-modules/pricing/aws"
  version = "2.0.3"
}

# Terraform backend configuration (storing state in S3)
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

# Provider configuration
provider "aws" {
  region = "us-east-1"
}

# Get the default VPC
data "aws_vpc" "default" {
  default = true
}

# Get the subnets of the default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "availability-zone"
    values = ["us-east-1a", "us-east-1b", "us-east-1c", "us-east-1d", "us-east-1f"]
  }
}

# Get default security group for the VPC
data "aws_security_group" "default" {
  vpc_id = data.aws_vpc.default.id
  filter {
    name   = "group-name"
    values = ["default"]
  }
}

# Create an EKS role for the cluster
resource "aws_iam_role" "eks_role" {
  name = "eks_cluster_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# Attach EKS policies to the role
resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role_policy_attachment" "eks_vpc_resource_controller_policy" {
  role       = aws_iam_role.eks_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
}

# Create an EKS Cluster
resource "aws_eks_cluster" "eks_cluster" {
  name     = "traffic-simulation-cluster"
  role_arn = aws_iam_role.eks_role.arn

  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [data.aws_security_group.default.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
    aws_iam_role_policy_attachment.eks_vpc_resource_controller_policy
  ]
}


# Create an EKS node group role
resource "aws_iam_role" "eks_node_group_role" {
  name = "eks_node_group_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# Attach policies to the node group role
resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "ec2_container_registry_read_only" {
  role       = aws_iam_role.eks_node_group_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Create an EKS node group
resource "aws_eks_node_group" "eks_node_group" {
  cluster_name    = aws_eks_cluster.eks_cluster.name
  node_group_name = "traffic-simulation-nodes"
  node_role_arn   = aws_iam_role.eks_node_group_role.arn
  subnet_ids      = data.aws_subnets.default.ids

  scaling_config {
    desired_size = 2
    max_size     = 3
    min_size     = 1
  }

  instance_types = ["t3.medium"]
}

# Create S3 bucket for traffic simulation data
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
  bucket     = aws_s3_bucket.traffic_simulation_bucket.id
  acl        = "private"
}

# Create SQS queues
resource "aws_sqs_queue" "standard_queue" {
  name = "SimulationEvents"
}

resource "aws_sqs_queue" "fifo_queue" {
  name                        = "SimCoreUpdates.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
}

# Create ECR repositories for each service
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
