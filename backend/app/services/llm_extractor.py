import openai
import asyncio
import json
import re
from typing import Dict, List, Optional, Any
from anthropic import Anthropic
from ..core.config import settings
from ..schemas.extraction import CategorizationResult, SalesExtraction, HousingExtraction

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_REGEX = re.compile(r"\+?\d[\d\s\-()]{6,}")

class LLMExtractor:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.rate_limit_delay = settings.LLM_RATE_LIMIT_DELAY
        self.max_retries = settings.MAX_RETRIES
    
    async def categorize_message(self, message_text: str) -> str:
        """Categorize a university group chat message using structured output."""
        system = "You classify university group chat messages. Return the category only."
        user = f"Message: {message_text}"
        try:
            response = await self._call_openai_structured(
                system=system,
                user=user,
                schema=CategorizationResult,
                max_tokens=5,
            )
            return response.category
        except Exception as e:
            print(f"Error categorizing message: {e}")
            return "GENERAL"
    
    async def extract_item_data(self, message_text: str) -> Optional[Dict[str, Any]]:
        """Extract structured item-for-sale data using structured outputs."""
        system = (
            "You extract item-for-sale details from student marketplace messages. "
            "Return a JSON object that conforms to the provided schema."
        )
        user = f"Message: {message_text}"
        try:
            model_obj = await self._call_openai_structured(
                system=system,
                user=user,
                schema=SalesExtraction,
                max_tokens=350,
            )
            # Fill contact hints if missing
            data = model_obj.dict()
            if not data.get("contact_phone"):
                phone_match = PHONE_REGEX.search(message_text)
                if phone_match:
                    data["contact_phone"] = re.sub(r"[^\d+]", "", phone_match.group(0))
            if not data.get("contact_email"):
                email_match = EMAIL_REGEX.search(message_text)
                if email_match:
                    data["contact_email"] = email_match.group(0)
            return data
        except Exception as e:
            print(f"Error extracting item data: {e}")
            return None
    
    async def extract_housing_data(self, message_text: str) -> Optional[Dict[str, Any]]:
        """Extract structured housing data using structured outputs."""
        system = (
            "You extract apartment/sublet/roommate listing details from messages. "
            "Return a JSON object that conforms to the provided schema."
        )
        user = f"Message: {message_text}"
        try:
            model_obj = await self._call_openai_structured(
                system=system,
                user=user,
                schema=HousingExtraction,
                max_tokens=400,
            )
            data = model_obj.dict()
            if not data.get("contact_phone"):
                phone_match = PHONE_REGEX.search(message_text)
                if phone_match:
                    data["contact_phone"] = re.sub(r"[^\d+]", "", phone_match.group(0))
            if not data.get("contact_email"):
                email_match = EMAIL_REGEX.search(message_text)
                if email_match:
                    data["contact_email"] = email_match.group(0)
            return data
        except Exception as e:
            print(f"Error extracting housing data: {e}")
            return None
    
    async def batch_categorize(self, messages: List[str]) -> List[str]:
        results = []
        for message in messages:
            result = await self.categorize_message(message)
            results.append(result)
            await asyncio.sleep(self.rate_limit_delay)
        return results
    
    async def _call_openai_structured(self, system: str, user: str, schema: Any, max_tokens: int = 300):
        """Call OpenAI with response_format schema for structured outputs, then validate via Pydantic."""
        json_schema = schema.model_json_schema()
        for attempt in range(self.max_retries):
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.1,
                    max_tokens=max_tokens,
                    response_format={"type": "json_schema", "json_schema": {"name": schema.__name__, "schema": json_schema}},
                )
                content = completion.choices[0].message.content
                if isinstance(content, str):
                    parsed_json = json.loads(content)
                else:
                    # Some SDK versions may return list of parts
                    text_parts = [p.get("text", "") for p in content if isinstance(p, dict)]
                    parsed_json = json.loads("".join(text_parts))
                return schema.model_validate(parsed_json)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                wait_time = (2 ** attempt) * self.rate_limit_delay
                await asyncio.sleep(wait_time)
        raise Exception("Max retries exceeded")

    def _sanitize_json_string(self, text: str) -> str:
        """Sanitize a string to make it valid JSON."""
        # Remove or replace common problematic control characters
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
        sanitized = sanitized.replace('\r\n', '\n').replace('\r', '\n')
        return sanitized