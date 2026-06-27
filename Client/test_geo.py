import asyncio
import httpx
import json

async def test():
    # Example coordinates for Ho Chi Minh City
    lat, lon = 10.762622, 106.660172
    NOMINATIM_URL = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&accept-language=vi"
    
    headers = {"User-Agent": "AuEdu_PC_App (chanhhiep.vn@gmail.com)"}
    async with httpx.AsyncClient() as client:
        res = await client.get(NOMINATIM_URL, headers=headers)
        
        # IP-API fallback
        res2 = await client.get("http://ip-api.com/json/?lang=vi")
        
        with open("geo_out.txt", "w", encoding="utf-8") as f:
            f.write("Nominatim: " + json.dumps(res.json().get('address'), ensure_ascii=False) + "\n")
            f.write("IP-API: " + json.dumps(res2.json(), ensure_ascii=False) + "\n")

asyncio.run(test())
