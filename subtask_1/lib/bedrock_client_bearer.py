"""
Bedrock client with Bearer Token (API Key) authentication.
For use with Bedrock API Keys (tokens starting with ABSK).
"""

import os
import json
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class BedrockClientBearer:
    """
    Bedrock client using Bearer Token authentication.
    Works with Bedrock API Keys (ABSK tokens).
    """
    
    def __init__(
        self,
        model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name: str = None,
        bearer_token: str = None,
        max_retries: int = 5,
        base_delay: float = 2.0,
        timeout: int = 120
    ):
        """
        Initialize the Bedrock client with bearer token auth.
        
        Args:
            model_id: The model ID to use
            region_name: AWS region (default: from env or us-east-1)
            bearer_token: Bedrock API Key (default: from env AWS_BEARER_TOKEN_BEDROCK)
            max_retries: Max retries for rate limiting
            base_delay: Base delay for exponential backoff
            timeout: Request timeout in seconds
        """
        self.model_id = model_id
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout
        
        # Get region
        self.region_name = region_name or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        
        # Get bearer token
        self.bearer_token = bearer_token or os.getenv('AWS_BEARER_TOKEN_BEDROCK')
        
        if not self.bearer_token:
            raise ValueError("Bearer token required. Set AWS_BEARER_TOKEN_BEDROCK env var or pass bearer_token parameter.")
        
        # Build endpoint URL
        self.endpoint = f"https://bedrock-runtime.{self.region_name}.amazonaws.com"
        
        # Track statistics
        self.total_calls = 0
        self.total_retries = 0
        self.last_call_time = None
        
        logger.info(f"Initialized BedrockClientBearer with model {model_id} in region {self.region_name}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        top_k: int = 100,
        max_tokens: int = 4096
    ) -> str:
        """
        Generate a response from the model.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Temperature (0.0-1.0)
            top_k: Top-k sampling
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        self.total_calls += 1
        
        # Build request based on model type
        if 'anthropic' in self.model_id.lower() or 'claude' in self.model_id.lower():
            body = self._build_anthropic_request(prompt, system_prompt, temperature, top_k, max_tokens)
        elif 'qwen' in self.model_id.lower():
            body = self._build_qwen_request(prompt, system_prompt, temperature, top_k, max_tokens)
        else:
            # Generic format
            body = self._build_generic_request(prompt, system_prompt, temperature, max_tokens)
        
        # Make request with retries
        url = f"{self.endpoint}/model/{self.model_id}/invoke"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.bearer_token}"
        }
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Rate limiting
                if self.last_call_time:
                    elapsed = time.time() - self.last_call_time
                    if elapsed < 0.5:
                        time.sleep(0.5 - elapsed)
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=body,
                    timeout=self.timeout
                )
                
                self.last_call_time = time.time()
                
                if response.status_code == 200:
                    return self._parse_response(response.json())
                elif response.status_code == 429:
                    # Rate limited
                    if attempt < self.max_retries:
                        delay = self.base_delay * (2 ** attempt)
                        self.total_retries += 1
                        print(f"    ⚠ Rate limited, waiting {delay:.1f}s (retry {attempt + 1}/{self.max_retries})...")
                        time.sleep(delay)
                        continue
                    else:
                        raise Exception(f"Rate limited after {self.max_retries} retries")
                else:
                    error_msg = response.text
                    raise Exception(f"Bedrock error {response.status_code}: {error_msg}")
                    
            except requests.exceptions.Timeout:
                last_error = Exception("Request timed out")
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    self.total_retries += 1
                    print(f"    ⚠ Timeout, waiting {delay:.1f}s (retry {attempt + 1}/{self.max_retries})...")
                    time.sleep(delay)
                    continue
                    
            except Exception as e:
                last_error = e
                if attempt < self.max_retries and 'throttl' in str(e).lower():
                    delay = self.base_delay * (2 ** attempt)
                    self.total_retries += 1
                    time.sleep(delay)
                    continue
                raise
        
        raise last_error
    
    def _build_anthropic_request(self, prompt, system_prompt, temperature, top_k, max_tokens):
        """Build request body for Anthropic/Claude models."""
        messages = [{"role": "user", "content": prompt}]
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_k": top_k,
            "messages": messages
        }
        
        if system_prompt:
            body["system"] = system_prompt
        
        return body
    
    def _build_qwen_request(self, prompt, system_prompt, temperature, top_k, max_tokens):
        """Build request body for Qwen models."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_k": top_k
        }
    
    def _build_generic_request(self, prompt, system_prompt, temperature, max_tokens):
        """Build generic request body."""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        return {
            "prompt": full_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    
    def _parse_response(self, response_json):
        """Parse response based on model type."""
        # Anthropic format
        if 'content' in response_json:
            content = response_json['content']
            if isinstance(content, list) and len(content) > 0:
                return content[0].get('text', '')
        
        # Qwen/generic format
        if 'choices' in response_json:
            choices = response_json['choices']
            if isinstance(choices, list) and len(choices) > 0:
                message = choices[0].get('message', {})
                return message.get('content', '')
        
        # Direct text
        if 'text' in response_json:
            return response_json['text']
        
        # Fallback
        return str(response_json)
    
    def get_stats(self):
        """Get call statistics."""
        return {
            'total_calls': self.total_calls,
            'total_retries': self.total_retries,
            'retry_rate': self.total_retries / self.total_calls if self.total_calls > 0 else 0
        }


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Load credentials
    from load_credentials import load_credentials_from_file
    load_credentials_from_file()
    
    client = BedrockClientBearer()
    
    response = client.generate(
        prompt="What is 2+2?",
        system_prompt="You are a helpful assistant. Be concise."
    )
    
    print(f"Response: {response}")
