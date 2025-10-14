// Production environment root module.
// TODO: Harden production state management and integrate monitoring modules.

terraform {
  required_version = ">= 1.6.0"
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for prod workloads."
  type        = string
  default     = "us-east-1"
}
