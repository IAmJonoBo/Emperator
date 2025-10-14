// Dev environment root module.

terraform {
  required_version = ">= 1.6.0"
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for dev workloads."
  type        = string
  default     = "us-east-1"
}
