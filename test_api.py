import sys
sys.path.insert(0, '/app/src')
import aiohttp, asyncio
from config import config

async def test():
    url = config.XUI_API_URL + '/panel/api/inbounds/get/1'
    headers = {'Authorization': 'Bearer ' + config.XUI_API_TOKEN}
    print('URL:', url)
    print('Token:', config.XUI_API_TOKEN[:10] + '...')
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=headers, ssl=False) as r:
            print('Status:', r.status)
            body = await r.text()
            print('Body:', body[:500])

asyncio.run(test())
