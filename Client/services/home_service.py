# Client/services/home_service.py
import asyncio
import datetime
from core.cache import app_cache
from core.config import get_supabase_client

class HomeService:
    @staticmethod
    async def get_news(ttl: int = 300) -> list:
        # Hàm fetcher thực sự gọi API
        async def fetcher():
            client = await get_supabase_client()
            res = await client.get("/thongbao", params={
                "select": "*",
                "order": "created_at.desc",
                "limit": "3"
            })
            res.raise_for_status()
            return res.json()

        # Trả về dữ liệu từ Cache hoặc fetch mới nếu hết TTL
        return await app_cache.get("cached_news", ttl, fetcher, default=[])

    @staticmethod
    async def get_schedule(gv_id: str, ttl: int = 300) -> list:
        if gv_id == "N/A":
            return []

        async def fetcher():
            client = await get_supabase_client()
            res = await client.get("/thoikhoabieu", params={
                "select": "id,lop_id,lop(tenlop),hocphan(tenhocphan,sobuoi),hocky(namhoc,tenhocky)",
                "giangvien_id": f"eq.{gv_id}"
            })
            res.raise_for_status()
            all_tkb = res.json()
            if not all_tkb:
                return []
            
            # Logic lọc học kỳ mới nhất
            valid_hks = [s["hocky"] for s in all_tkb if s.get("hocky")]
            if not valid_hks:
                return all_tkb
            namhocs = sorted(set(hk["namhoc"] for hk in valid_hks), reverse=True)
            latest_hk = [hk for hk in valid_hks if hk["namhoc"] == namhocs[0]][0]["tenhocky"]
            return [s for s in all_tkb if s.get("hocky") and s["hocky"]["namhoc"] == namhocs[0] and s["hocky"]["tenhocky"] == latest_hk]

        return await app_cache.get(f"cached_home_schedule_{gv_id}", ttl, fetcher, default=[])

    @staticmethod
    async def get_today_classes(gv_id: str, ttl: int = 300) -> dict:
        if gv_id == "N/A":
            return {"classes": []}

        async def fetcher():
            client = await get_supabase_client()
            # 1. Lấy TKB
            res_all = await client.get("/thoikhoabieu", params={
                "select": "id,lop_id,lop(tenlop),hocphan(tenhocphan)",
                "giangvien_id": f"eq.{gv_id}"
            })
            res_all.raise_for_status()
            all_tkb = res_all.json()
            if not all_tkb:
                return {"classes": []}

            # 2. Lấy tiết hôm nay
            today_date = datetime.datetime.now(datetime.timezone.utc).astimezone().date()
            thu_hom_nay = today_date.weekday() + 2
            tkb_ids_str = ",".join(str(x["id"]) for x in all_tkb)
            
            res_tiet = await client.get("/tkb_tiet", params={
                "select": "id,tkb_id,thu,phong_hoc,tiet(thoigianbd,thoigiankt)",
                "tkb_id": f"in.({tkb_ids_str})",
                "thu": f"eq.{thu_hom_nay}",
                "order": "tiet(thoigianbd).asc"
            })
            res_tiet.raise_for_status()
            tiet_list = res_tiet.json()
            if not tiet_list:
                return {"classes": []}

            # 3. Lấy trạng thái điểm danh
            tiet_ids_str = ",".join(str(t["id"]) for t in tiet_list)
            res_dd = await client.get("/diemdanh", params={
                "select": "tkb_tiet_id",
                "tkb_tiet_id": f"in.({tiet_ids_str})",
                "ngay_diem_danh": f"eq.{today_date.isoformat()}"
            })
            res_dd.raise_for_status()
            dd_map = {str(d["tkb_tiet_id"]) for d in res_dd.json()}

            tkb_dict = {x["id"]: x for x in all_tkb}
            classes = []
            for t in tiet_list:
                tkb_info = tkb_dict.get(t["tkb_id"])
                if tkb_info:
                    classes.append({
                        "id": t["id"],
                        "ten_hp": tkb_info.get("hocphan", {}).get("tenhocphan", "N/A"),
                        "ten_lop": tkb_info.get("lop", {}).get("tenlop", "N/A"),
                        "phong_hoc": t.get("phong_hoc", "N/A"),
                        "thoigianbd": t.get("tiet", {}).get("thoigianbd"),
                        "thoigiankt": t.get("tiet", {}).get("thoigiankt"),
                        "da_diem_danh": str(t["id"]) in dd_map
                    })
            return {"classes": classes}

        return await app_cache.get(f"cached_today_{gv_id}", ttl, fetcher, default={"classes": []})

    @classmethod
    async def get_all_home_data(cls, gv_id: str, ttl: int = 300):
        """Hàm gom để gọi song song tất cả các API của trang Home"""
        return await asyncio.gather(
            cls.get_news(ttl),
            cls.get_schedule(gv_id, ttl),
            cls.get_today_classes(gv_id, ttl),
            return_exceptions=True
        )