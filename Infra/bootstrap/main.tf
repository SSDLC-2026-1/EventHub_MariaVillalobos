terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "tf_state" {
  bucket = "eventhub-terraform-state-sara-palacios-2026"

  tags = {
    Name        = "eventhub-terraform-state"
    Environment = "Lab"
    Managed_By  = "Terraform"
  }
}

resource "aws_s3_bucket_versioning" "tf_state_versioning" {
  bucket = aws_s3_bucket.tf_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

output "state_bucket_name" {
  value = aws_s3_bucket.tf_state.bucket
}