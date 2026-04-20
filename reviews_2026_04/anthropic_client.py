"""
Anthropic client class for interacting with Claude models.
Same interface as BedrockClient/TogetherClient (generate + get_stats).
"""

import logging
import os
import time

from anthropic import Anthropic


logger = logging.getLogger(__name__)


class AnthropicClient:
    """Client wrapper with retry logic and usage stats."""

    def __init__(
        self,
        model_id: str = "claude-3-5-sonnet-latest",
        api_key: str | None = None,
        max_retries: int = 5,
        base_delay: float = 2.0,
        timeout: int = 120,
        max_tokens: int = 512,
    ):
        self.model_id = model_id
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout
        self.max_tokens = max_tokens

        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY env var "
                "or pass api_key parameter."
            )

        self.client = Anthropic(api_key=key, timeout=timeout)
        self.total_calls = 0
        self.total_retries = 0
        self.last_call_time = None

        logger.info("Initialized AnthropicClient with model %s", model_id)
        logger.info(
            "  Max retries: %d, Base delay: %.1fs, Timeout: %ds",
            max_retries, base_delay, timeout
        )

    def generate(self, prompt, system_prompt=None, temperature=0.7, top_k=100):
        """Generate model response with retry logic.

        Note: `top_k` is accepted for interface compatibility but ignored by the
        Anthropic Messages API in this wrapper.
        """
        del top_k
        self.total_calls += 1
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if self.last_call_time:
                    elapsed = time.time() - self.last_call_time
                    if elapsed < 0.5:
                        time.sleep(0.5 - elapsed)

                response = self.client.messages.create(
                    model=self.model_id,
                    max_tokens=self.max_tokens,
                    temperature=temperature,
                    system=system_prompt or "",
                    messages=[{"role": "user", "content": prompt}],
                )
                self.last_call_time = time.time()

                parts = []
                for block in response.content:
                    if getattr(block, "type", None) == "text":
                        parts.append(block.text)
                return "".join(parts).strip()

            except Exception as err:
                last_error = err
                err_str = str(err).lower()
                is_throttle = any(
                    kw in err_str
                    for kw in ["rate", "throttl", "too many", "429", "503", "unavailable"]
                )
                if attempt < self.max_retries:
                    if is_throttle:
                        delay = self.base_delay * (2 ** attempt) + (time.time() % 1)
                    else:
                        delay = self.base_delay * (2 ** attempt)
                    self.total_retries += 1
                    label = "Rate limited" if is_throttle else "Error"
                    logger.warning(
                        "%s (attempt %d): %s. Retrying in %.1fs...",
                        label, attempt + 1, err, delay
                    )
                    print(f"    ⚠ {label}, waiting {delay:.1f}s (retry {attempt + 1}/{self.max_retries})...")
                    time.sleep(delay)
                    continue
                raise

        raise last_error

    def get_stats(self):
        return {
            "total_calls": self.total_calls,
            "total_retries": self.total_retries,
            "retry_rate": self.total_retries / self.total_calls if self.total_calls > 0 else 0,
        }

