import sys, os
sys.path.insert(0, os.path.abspath("backend"))
import httpx, asyncio
from app.config import settings

async def test_openai():
    api_url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            res = await client.post(
                api_url,
                json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
                headers=headers
            )
            print("Status code:", res.status_code)
            print("Response:", res.text[:200])
        except Exception as e:
            print("Exception:", type(e), e)

asyncio.run(test_openai())
