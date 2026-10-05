# practice_async.py
import asyncio
import aiohttp


async def fetch_example():
    """Practice async HTTP."""
    url = "https://api.github.com/repos/python/cpython"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            print(f"✅ Fetched: {data['name']}")
            return data


# Run it
asyncio.run(fetch_example())
