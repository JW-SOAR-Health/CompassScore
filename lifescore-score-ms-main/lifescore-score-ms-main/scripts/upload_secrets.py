"""
Script to upload environment variables to AWS Secrets Manager.

This script loads variables from a .env file and uploads them as a secret to AWS
Secrets Manager.
"""

import json
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import NoCredentialsError, ClientError, BotoCoreError

# Load environment variables from the .env file
load_dotenv()

# Fetch secret name and AWS region from environment variables
SECRET_NAME = os.getenv("SECRET_NAME")
AWS_REGION = os.getenv("AWS_REGION")


# Initialize the Secrets Manager client
CLIENT = None
if AWS_REGION and SECRET_NAME:
    try:
        CLIENT = boto3.client("secretsmanager", region_name=AWS_REGION)
    except NoCredentialsError:
        print("AWS credentials not found. Skipping secrets upload.")
    except BotoCoreError as boto_err:
        print(f"Error initializing boto3 client: {boto_err}")
else:
    print("AWS_REGION or SECRET_NAME is not set. Skipping secrets upload.")


def create_or_update_secret(secret_name: str, secret_value: str) -> None:
    """
    Creates a new secret or updates an existing one in AWS Secrets Manager.

    Args:
        secret_name (str): The name of the secret in AWS Secrets Manager.
        secret_value (str): The value of the secret as a JSON string.
    """
    if not CLIENT:
        print("Skipping secret creation/update due to missing AWS credentials.")
        return

    try:
        # Try to create the secret
        CLIENT.create_secret(Name=secret_name, SecretString=secret_value)
        print(f"Secret {secret_name} created successfully.")
    except CLIENT.exceptions.ResourceExistsException:
        # If the secret already exists, update it
        CLIENT.update_secret(SecretId=secret_name, SecretString=secret_value)
        print(f"Secret {secret_name} updated successfully.")
    except ClientError as client_err:
        print(f"Failed to create or update secret: {client_err}")


def main() -> None:
    """
    Main function to load environment variables and store them as a secret in AWS
    Secrets Manager.
    """
    if not CLIENT:
        print("Skipping secret upload due to missing AWS credentials.")
        return

    # Create a dictionary from the .env variables
    secret_dict = {key: os.getenv(key) for key in os.environ if key}

    # Convert the dictionary to a JSON string
    secret_string = json.dumps(secret_dict)
    if not SECRET_NAME:
        raise ValueError("SECRET_NAME environment variable must be set.")

    # Create or update the secret in AWS Secrets Manager
    create_or_update_secret(SECRET_NAME, secret_string)


if __name__ == "__main__":
    main()
