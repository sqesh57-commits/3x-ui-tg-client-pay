import aiohttp
import uuid
import json
import logging
import random
from datetime import datetime, timedelta, timezone
from config import config

logger = logging.getLogger(__name__)


class XUIAPI:
    def __init__(self):
        self.session = None
        self.cookie_jar = aiohttp.CookieJar(unsafe=True)

    async def login(self):
        try:
            connector = aiohttp.TCPConnector(ssl=config.XUI_VERIFY_SSL)
            self.session = aiohttp.ClientSession(
                connector=connector,
                cookie_jar=self.cookie_jar,
                trust_env=True
            )

            base_url = config.XUI_API_URL.rstrip('/')
            login_url = f"{base_url}/login"

            async with self.session.post(login_url, data={
                "username": config.XUI_USERNAME,
                "password": config.XUI_PASSWORD
            }) as resp:
                if resp.status != 200:
                    logger.error(f"Login failed with status: {resp.status}")
                    return False

                try:
                    response = await resp.json()
                    if response.get("success"):
                        logger.info("Login successful")
                        return True
                    else:
                        logger.error(f"Login failed: {response.get('msg')}")
                        return False
                except Exception:
                    text = await resp.text()
                    if "success" in text.lower():
                        return True
                    logger.error(f"Login failed. Response: {text[:100]}...")
                    return False
        except Exception as e:
            logger.exception(f"Login error: {e}")
            return False

    async def get_inbound(self, inbound_id: int):
        try:
            base_url = config.XUI_API_URL.rstrip('/')
            base_path = config.XUI_BASE_PATH.strip('/')
            if base_path:
                base_url = f"{base_url}/{base_path}"
            url = f"{base_url}/api/inbounds/get/{inbound_id}"

            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None

                try:
                    data = await resp.json()
                    if data.get("success"):
                        return data.get("obj")
                    return None
                except Exception:
                    return None
        except Exception as e:
            logger.exception(f"Get inbound error: {e}")
            return None

    async def update_inbound(self, inbound_id: int, data: dict):
        try:
            base_url = config.XUI_API_URL.rstrip('/')
            base_path = config.XUI_BASE_PATH.strip('/')
            if base_path:
                base_url = f"{base_url}/{base_path}"
            url = f"{base_url}/api/inbounds/update/{inbound_id}"

            async with self.session.post(url, json=data) as resp:
                if resp.status != 200:
                    return False

                try:
                    response = await resp.json()
                    return response.get("success", False)
                except Exception:
                    text = await resp.text()
                    return "success" in text.lower()
        except Exception as e:
            logger.exception(f"Update inbound error: {e}")
            return False

    async def _get_flow_from_inbound(self, inbound: dict) -> str:
        try:
            settings = json.loads(inbound.get("settings", "{}"))
            stream_settings = json.loads(inbound.get("streamSettings", "{}"))
            reality_settings = stream_settings.get("realitySettings", {})

            if reality_settings:
                clients = settings.get("clients", [])
                if clients and len(clients) > 0:
                    existing_flow = clients[0].get("flow", "")
                    if existing_flow:
                        return existing_flow
                return reality_settings.get("flow", "")

            clients = settings.get("clients", [])
            if clients and len(clients) > 0:
                existing_flow = clients[0].get("flow", "")
                if existing_flow:
                    return existing_flow
        except Exception as e:
            logger.warning(f"Could not get flow from inbound: {e}")

        return ""

    async def create_vless_profile(self, telegram_id: int, expiry_time: int = 0):
        if not await self.login():
            return None

        if expiry_time < 0:
            expiry_time = 0

        inbound = await self.get_inbound(config.INBOUND_ID)
        if not inbound:
            return None

        try:
            settings = json.loads(inbound["settings"])
            clients = settings.get("clients", [])

            client_id = str(uuid.uuid4())
            email = f"user_{telegram_id}_{random.randint(1000, 9999)}"
            flow = await self._get_flow_from_inbound(inbound)
            sub_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"user_{telegram_id}"))

            new_client = {
                "id": client_id,
                "flow": flow,
                "email": email,
                "limitIp": 0,
                "totalGB": 0,
                "expiryTime": expiry_time * 1000,
                "enable": True,
                "tgId": "",
                "subId": sub_id,
                "reset": 0,
                "fingerprint": config.REALITY_FINGERPRINT,
                "publicKey": config.REALITY_PUBLIC_KEY,
                "shortId": config.REALITY_SHORT_ID,
                "spiderX": config.REALITY_SPIDER_X
            }

            if expiry_time < 1577836800:
                new_client["expiryTime"] = 0
            elif expiry_time > 2000000000:
                new_client["expiryTime"] = 0

            clients.append(new_client)
            settings["clients"] = clients

            update_data = {
                "up": inbound["up"],
                "down": inbound["down"],
                "total": inbound["total"],
                "remark": inbound["remark"],
                "enable": inbound["enable"],
                "expiryTime": inbound["expiryTime"],
                "listen": inbound["listen"],
                "port": inbound["port"],
                "protocol": inbound["protocol"],
                "settings": json.dumps(settings, indent=2),
                "streamSettings": inbound["streamSettings"],
                "sniffing": inbound["sniffing"],
            }

            if await self.update_inbound(config.INBOUND_ID, update_data):
                return {
                    "client_id": client_id,
                    "email": email,
                    "port": inbound["port"],
                    "security": "reality",
                    "remark": inbound["remark"],
                    "sni": config.REALITY_SNI,
                    "pbk": config.REALITY_PUBLIC_KEY,
                    "fp": config.REALITY_FINGERPRINT,
                    "sid": config.REALITY_SHORT_ID,
                    "spx": config.REALITY_SPIDER_X,
                    "sub_id": sub_id
                }
            return None
        except Exception as e:
            logger.exception(f"Create profile error: {e}")
            return None

    async def update_client_expiry(self, email: str, expiry_time: int):
        if not await self.login():
            return False

        if expiry_time < 0:
            expiry_time = 0

        try:
            inbound = await self.get_inbound(config.INBOUND_ID)
            if not inbound:
                return False

            settings = json.loads(inbound["settings"])
            clients = settings.get("clients", [])

            updated = False
            for client in clients:
                if client["email"] == email:
                    final_expiry_time = expiry_time
                    if expiry_time < 1577836800:
                        final_expiry_time = 0
                    elif expiry_time > 2000000000:
                        final_expiry_time = 0
                    client["expiryTime"] = final_expiry_time * 1000
                    updated = True
                    break

            if not updated:
                return False

            settings["clients"] = clients

            update_data = {
                "up": inbound["up"],
                "down": inbound["down"],
                "total": inbound["total"],
                "remark": inbound["remark"],
                "enable": inbound["enable"],
                "expiryTime": inbound["expiryTime"],
                "listen": inbound["listen"],
                "port": inbound["port"],
                "protocol": inbound["protocol"],
                "settings": json.dumps(settings, indent=2),
                "streamSettings": inbound["streamSettings"],
                "sniffing": inbound["sniffing"],
            }

            return await self.update_inbound(config.INBOUND_ID, update_data)
        except Exception as e:
            logger.exception(f"Update client expiry error: {e}")
            return False

    async def get_user_stats(self, email: str):
        if not await self.login():
            return {"upload": 0, "download": 0}

        try:
            base_url = config.XUI_API_URL.rstrip('/')
            base_path = config.XUI_BASE_PATH.strip('/')
            if base_path:
                base_url = f"{base_url}/{base_path}"
            url = f"{base_url}/api/inbounds/getClientTraffics/{email}"

            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return {"upload": 0, "download": 0}

                try:
                    data = await resp.json()
                    if data.get("success"):
                        client_data = data.get("obj")
                        if isinstance(client_data, dict):
                            return {
                                "upload": client_data.get("up", 0),
                                "download": client_data.get("down", 0)
                            }
                except Exception:
                    return {"upload": 0, "download": 0}
        except Exception as e:
            logger.error(f"Stats error: {e}")
        return {"upload": 0, "download": 0}

    async def get_online_users(self):
        if not await self.login():
            return 0

        try:
            base_url = config.XUI_API_URL.rstrip('/')
            base_path = config.XUI_BASE_PATH.strip('/')
            if base_path:
                base_url = f"{base_url}/{base_path}"
            url = f"{base_url}/api/inbounds/onlines"

            async with self.session.post(url) as resp:
                if resp.status != 200:
                    return 0

                try:
                    data = await resp.json()
                    online = 0
                    if data.get("success"):
                        users = data.get("obj")
                        if isinstance(users, list):
                            for user in users:
                                if str(user).startswith("user_"):
                                    online += 1
                    return online
                except Exception:
                    return 0
        except Exception as e:
            logger.error(f"Online users error: {e}")
        return 0

    async def close(self):
        if self.session:
            await self.session.close()


# === Wrapper functions ===

async def create_vless_profile(telegram_id: int, expiry_time: int = 0):
    api = XUIAPI()
    try:
        return await api.create_vless_profile(telegram_id, expiry_time)
    finally:
        await api.close()


async def update_client_expiry(email: str, expiry_time: int):
    api = XUIAPI()
    try:
        return await api.update_client_expiry(email, expiry_time)
    finally:
        await api.close()


async def get_online_users():
    api = XUIAPI()
    try:
        return await api.get_online_users()
    finally:
        await api.close()


async def get_user_stats(email: str):
    api = XUIAPI()
    try:
        return await api.get_user_stats(email)
    finally:
        await api.close()


def generate_sub_url(sub_id: str) -> str:
    if not config.SUBSCRIPTION_URL_BASE:
        from urllib.parse import urlparse
        parsed = urlparse(config.XUI_API_URL)
        scheme = parsed.scheme or "http"
        host = parsed.hostname or "localhost"
        return f"{scheme}://{host}:{config.XUI_SUB_PORT}/sub/{sub_id}"
    return f"{config.SUBSCRIPTION_URL_BASE.rstrip('/')}:{config.XUI_SUB_PORT}/sub/{sub_id}"


def generate_vless_url(profile_data: dict) -> str:
    remark = profile_data.get('remark', '')
    email = profile_data['email']
    fragment = f"{remark}-{email}" if remark else email

    return (
        f"vless://{profile_data['client_id']}@{config.XUI_HOST}:{profile_data['port']}"
        f"?type=tcp&security=reality"
        f"&pbk={config.REALITY_PUBLIC_KEY}"
        f"&fp={config.REALITY_FINGERPRINT}"
        f"&sni={config.REALITY_SNI}"
        f"&sid={config.REALITY_SHORT_ID}"
        f"&spx={config.REALITY_SPIDER_X}"
        f"#{fragment}"
    )


def get_safe_expiry_timestamp(subscription_end) -> int:
    if subscription_end is None:
        return 0

    if isinstance(subscription_end, str):
        try:
            subscription_end = datetime.fromisoformat(subscription_end)
        except Exception:
            return 0

    if not isinstance(subscription_end, datetime):
        return 0

    now = datetime.now(timezone.utc)

    if subscription_end < datetime(2020, 1, 1, tzinfo=timezone.utc):
        return 0

    if subscription_end > now + timedelta(days=3650):
        return 0

    if subscription_end <= now:
        return 0

    try:
        timestamp = int(subscription_end.timestamp())
        if timestamp < 0 or timestamp < 1577836800:
            return 0
        return timestamp
    except Exception:
        return 0


async def force_update_profile_expiry(email: str, subscription_end) -> bool:
    try:
        expiry_time = get_safe_expiry_timestamp(subscription_end)
        return await update_client_expiry(email, expiry_time)
    except Exception as e:
        logger.error(f"Error force updating profile {email}: {e}")
        return False
