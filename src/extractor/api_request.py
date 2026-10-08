"""Bounded retries for DeepSeek completion requests, without logging credentials."""
import asyncio
import json
import logging
import aiohttp

logger = logging.getLogger(__name__)


async def request_completion(session, api_url, api_key, payload, timeout=60,
                             max_attempts=3, retry_delay=2, validate=None):
    for attempt in range(max(1, max_attempts)):
        try:
            async with session.post(
                f"{api_url.rstrip('/')}/chat/completions", json=payload,
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status != 200:
                    logger.warning('DeepSeek HTTP %s (attempt %s/%s)', response.status, attempt + 1, max_attempts)
                    if response.status not in (408, 429, 500, 502, 503, 504):
                        return None
                else:
                    data = await response.json()
                    choice = data.get('choices', [{}])[0]
                    content = (choice.get('message', {}).get('content') or '').strip()
                    if not content or choice.get('finish_reason') == 'length':
                        raise ValueError('empty or truncated completion')
                    return validate(content) if validate else content
        except (asyncio.TimeoutError, aiohttp.ClientError, ValueError, KeyError, IndexError, TypeError) as error:
            logger.warning('DeepSeek response rejected (attempt %s/%s): %s', attempt + 1, max_attempts, error)
        if attempt + 1 < max_attempts:
            await asyncio.sleep(min(30, retry_delay * 2 ** attempt))
    return None


def parse_json_object(content):
    """Accept a JSON object or fenced object; schema validation is done by callers."""
    start = content.find('{')
    if start < 0:
        raise ValueError('missing JSON object')
    value, _ = json.JSONDecoder().raw_decode(content[start:])
    if not isinstance(value, dict):
        raise ValueError('expected JSON object')
    return value
