# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""
Bedrock client class for interacting with AWS Bedrock models.
"""

import logging
import os
import time
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config as BotoConfig


logger = logging.getLogger(__name__)


class BedrockClient:
    """
    A client for interacting with AWS Bedrock models using the Converse API.
    Includes retry logic with exponential backoff for rate limiting.
    """
    
    def __init__(
        self, 
        model_id="qwen.qwen3-32b-v1:0", 
        region_name=None, 
        bearer_token=None,
        max_retries=5,
        base_delay=2.0,
        timeout=120
    ):
        """
        Initialize the Bedrock client.
        
        Args:
            model_id (str): The model ID to use. Default is Qwen 3 32B.
            region_name (str, optional): AWS region name.
            bearer_token (str, optional): AWS bearer token.
            max_retries (int): Maximum number of retries for rate limiting. Default 5.
            base_delay (float): Base delay in seconds for exponential backoff. Default 2.0.
            timeout (int): Request timeout in seconds. Default 120.
        """
        self.model_id = model_id
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout
        
        # Get region from parameter, env var, or default
        self.region_name = region_name or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        # Get bearer token from parameter or env var
        token = bearer_token or os.getenv('AWS_BEARER_TOKEN_BEDROCK')
        
        # Configure boto with retries and timeout
        boto_config = BotoConfig(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            read_timeout=timeout,
            connect_timeout=30
        )
        
        # Set up client based on authentication method
        if token and token.startswith('ABSK'):
            # Bedrock API Key format - use bearer token authentication
            # This requires a custom session with bearer token
            from botocore.credentials import Credentials
            from botocore.auth import SigV4Auth
            
            # For Bedrock API Keys, we need to use the token directly in headers
            # Store token for use in requests
            self._bearer_token = token
            self.client = boto3.client(
                service_name='bedrock-runtime', 
                region_name=self.region_name, 
                config=boto_config
            )
            # Note: Bearer token will be added in generate() method
            self._use_bearer_auth = True
        elif token and ':' in token:
            # Standard AWS credentials format (access_key:secret_key)
            parts = token.split(':')
            session = boto3.Session(
                aws_access_key_id=parts[0],
                aws_secret_access_key=parts[1] if len(parts) > 1 else '',
                region_name=self.region_name
            )
            self.client = session.client(service_name='bedrock-runtime', config=boto_config)
            self._use_bearer_auth = False
        else:
            # Use default credentials (IAM role, env vars, etc.)
            self.client = boto3.client(
                service_name='bedrock-runtime', 
                region_name=self.region_name, 
                config=boto_config
            )
            self._use_bearer_auth = False
        
        # Track call statistics
        self.total_calls = 0
        self.total_retries = 0
        self.last_call_time = None
        
        logger.info(f"Initialized BedrockClient with model {model_id} in region {self.region_name}")
        logger.info(f"  Max retries: {max_retries}, Base delay: {base_delay}s, Timeout: {timeout}s")
    
    def generate(self, prompt, system_prompt=None, temperature=0.7, top_k=100):
        """
        Generate a response from the model with retry logic.
        
        Args:
            prompt (str): The user prompt/question to send to the model.
            system_prompt (str, optional): System prompt to guide model behavior.
            temperature (float): Temperature for response generation (0.0-1.0). Default is 0.7.
            top_k (int): Top-k sampling parameter. Default is 100.
        
        Returns:
            str: The generated text response from the model.
        
        Raises:
            ClientError: If there's an error communicating with AWS Bedrock after all retries.
        """
        self.total_calls += 1
        
        # Prepare system prompts
        system_prompts = []
        if system_prompt:
            system_prompts.append({"text": system_prompt})
        
        # Prepare messages
        messages = [{
            "role": "user",
            "content": [{"text": prompt}]
        }]
        
        # Inference configuration
        inference_config = {"temperature": temperature}
        additional_model_fields = {"top_k": top_k}
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Add delay between calls to avoid rate limiting
                if self.last_call_time:
                    elapsed = time.time() - self.last_call_time
                    if elapsed < 0.5:  # Minimum 0.5s between calls
                        time.sleep(0.5 - elapsed)
                
                logger.debug(f"Attempt {attempt + 1}/{self.max_retries + 1} for model {self.model_id}")
                
                # Send the message
                response = self.client.converse(
                    modelId=self.model_id,
                    messages=messages,
                    system=system_prompts if system_prompts else None,
                    inferenceConfig=inference_config,
                    additionalModelRequestFields=additional_model_fields
                )
                
                self.last_call_time = time.time()
                
                # Log token usage
                token_usage = response['usage']
                logger.debug(f"Tokens: in={token_usage['inputTokens']}, out={token_usage['outputTokens']}")
                
                # Extract and return the text response
                output_text = response['output']['message']['content'][0]['text']
                return output_text
                
            except ClientError as err:
                last_error = err
                error_code = err.response['Error']['Code']
                error_message = err.response['Error']['Message']
                
                # Check if it's a throttling/rate limit error
                is_throttle = error_code in [
                    'ThrottlingException', 
                    'TooManyRequestsException',
                    'ServiceUnavailableException',
                    'ModelStreamErrorException',
                    'ModelTimeoutException'
                ] or 'throttl' in error_message.lower() or 'rate' in error_message.lower()
                
                if is_throttle and attempt < self.max_retries:
                    # Exponential backoff with jitter
                    delay = self.base_delay * (2 ** attempt) + (time.time() % 1)
                    self.total_retries += 1
                    logger.warning(f"Rate limited (attempt {attempt + 1}). Waiting {delay:.1f}s... Error: {error_code}")
                    print(f"    ⚠ Rate limited, waiting {delay:.1f}s (retry {attempt + 1}/{self.max_retries})...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Bedrock error: {error_code} - {error_message}")
                    raise
                    
            except Exception as err:
                last_error = err
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    self.total_retries += 1
                    logger.warning(f"Error (attempt {attempt + 1}): {err}. Retrying in {delay:.1f}s...")
                    print(f"    ⚠ Connection error, waiting {delay:.1f}s (retry {attempt + 1}/{self.max_retries})...")
                    time.sleep(delay)
                    continue
                else:
                    raise
        
        # If we get here, all retries failed
        raise last_error
    
    def get_stats(self):
        """Get call statistics."""
        return {
            'total_calls': self.total_calls,
            'total_retries': self.total_retries,
            'retry_rate': self.total_retries / self.total_calls if self.total_calls > 0 else 0
        }


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Initialize client (will use environment variables if set)
    client = BedrockClient()
    
    # Generate a response
    response = client.generate(
        prompt="Create a list of 3 pop songs.",
        system_prompt="You are an app that creates playlists for a radio station that plays rock and pop music. Only return song names and the artist.",
        temperature=0.7,
        top_k=100
    )
    
    print("Response:")




