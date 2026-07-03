# FrostbiteVPN: доработка Telegram клиентского бота под контейнерный запуск и 3x-ui 3.4.x

## 0. Контекст

Репозиторий бота:

```text
https://github.com/sqesh57-commits/3x-ui-tg-client-pay
```

Репозиторий панели:

```text
https://github.com/sqesh57-commits/3x-ui-deploy-sq
```

Текущая инфраструктура FrostbiteVPN:

```text
Основной compose:
~/.openclaw/workspace/3x-ui-deploy-sq/compose.yml

Контейнер панели:
3x-ui-allinone

3x-ui version:
3.4.2

Панель:
https://panel.frostbite-rogueite22768.my-vm.work:20576

Внутренний порт панели:
21443

VLESS WS TLS:
external 443/tcp
internal inbound 127.0.0.1:37291

Reality + XTLS-Vision:
external/internal port 30443/tcp
inbound id: 3
remark: VLESS\Reality
listen: 0.0.0.0
protocol: vless

Custom address для клиентских VLESS-ссылок:
vless.frostbite-rogueite22768.my-vm.work

Subscription endpoint:
https://panel.frostbite-rogueite22768.my-vm.work:20576/frostbite-sub-8q2m7k/<subId>
```

Важно:

- Бот должен работать **только через 3x-ui API**.
- Бот **не должен читать SQLite напрямую**.
- SQLite использовалась только для диагностики структуры `stream_settings`.
- Бот должен запускаться **в Docker-контейнере**, не через systemd.
- Бот должен быть в одной Docker network с `3x-ui-allinone`.
- Наружу порты бота публиковать не нужно.
- `XUI_API_URL` для бота должен быть внутренним:

```env
XUI_API_URL=http://3x-ui-allinone:21443
```

---

## 1. Основные цели доработки

1. Подготовить бота к контейнерному запуску.
2. Добавить Dockerfile для бота.
3. Добавить compose-сервис бота.
4. Исправить `.env.example` под FrostbiteVPN.
5. Исправить парсинг Reality settings из API 3x-ui 3.4.x.
6. Исправить генерацию VLESS Reality ссылки:
   - добавить `flow=xtls-rprx-vision`;
   - добавить `encryption=none`;
   - корректно кодировать `spx=/` как `%2F`;
   - корректно кодировать fragment.
7. Исправить генерацию subscription URL под кастомный путь `/frostbite-sub-8q2m7k/`.
8. Убрать обязательность ручного указания `REALITY_PUBLIC_KEY`, `REALITY_SNI`, `REALITY_SHORT_ID` в `.env`.
9. Добавить диагностический CLI/script для проверки API, inbound и Reality settings.
10. Добавить минимальный healthcheck/logging.

---

## 2. Ожидаемая архитектура контейнеров

Итоговая схема:

```text
docker compose network
├── 3x-ui-allinone
│   ├── x-ui panel: 127.0.0.1:21443 внутри контейнера
│   ├── nginx external panel: 20576
│   ├── VLESS WS: 443
│   └── Reality: 30443
│
└── frostbite-tg-client-bot
    └── connects to http://3x-ui-allinone:21443
```

Бот не должен обращаться к:

```text
https://panel.frostbite-rogueite22768.my-vm.work:20576
```

для API, если работает в той же сети Docker.

---

## 3. Изменения в `.env.example`

Файл:

```text
src/.env.example
```

Привести к такому виду:

```env
# Telegram
BOT_TOKEN=
PAYMENT_TOKEN=
ADMINS=

# 3x-ui API internal Docker URL
XUI_API_URL=http://3x-ui-allinone:21443
XUI_VERIFY_SSL=False
XUI_USERNAME=admin
XUI_PASSWORD=

# 3x-ui inbound
INBOUND_ID=3

# Public address for generated VLESS links
XUI_HOST=vless.frostbite-rogueite22768.my-vm.work

# Subscription link generation
SUBSCRIPTION_URL_BASE=https://panel.frostbite-rogueite22768.my-vm.work:20576
XUI_SUB_PATH=/frostbite-sub-8q2m7k/
XUI_SUB_PORT=

# Optional fallback only. Normally parsed from 3x-ui API.
REALITY_PUBLIC_KEY=
REALITY_SNI=
REALITY_SHORT_ID=
REALITY_FINGERPRINT=chrome
REALITY_SPIDER_X=/

# Optional external nginx BasicAuth.
# Not needed when XUI_API_URL is internal Docker URL.
NGINX_BASIC_AUTH_USER=
NGINX_BASIC_AUTH_PASSWORD=

# Local admin panel / debug
ADMIN_PANEL_PASSWORD=
ENABLE_CODE_EDITOR=false
```

---

## 4. Изменения в `src/config.py`

### 4.1 Добавить новые поля

Добавить:

```python
XUI_SUB_PATH: str = os.getenv("XUI_SUB_PATH", "/sub/")
```

### 4.2 Reality fallback должен читаться из env

Сейчас поля могут быть пустыми константами. Нужно сделать так:

```python
REALITY_PUBLIC_KEY: str = os.getenv("REALITY_PUBLIC_KEY", "")
REALITY_SNI: str = os.getenv("REALITY_SNI", "")
REALITY_SHORT_ID: str = os.getenv("REALITY_SHORT_ID", "")
REALITY_FINGERPRINT: str = os.getenv("REALITY_FINGERPRINT", "chrome")
REALITY_SPIDER_X: str = os.getenv("REALITY_SPIDER_X", "/")
```

### 4.3 `XUI_SUB_PORT`

Сделать строкой, допускающей пустое значение:

```python
XUI_SUB_PORT: str = os.getenv("XUI_SUB_PORT", "")
```

---

## 5. Изменения в `src/functions.py`

### 5.1 Общие требования

- Не читать SQLite.
- Все данные брать из API `/api/inbounds/get/{INBOUND_ID}`.
- Парсер должен поддерживать оба варианта ключей:
  - camelCase из API: `streamSettings`, `expiryTime`;
  - snake_case из БД/старых структур: `stream_settings`, `expiry_time`.
- Для 3x-ui 3.4.x Reality данные находятся так:

```json
{
  "streamSettings": {
    "network": "tcp",
    "security": "reality",
    "realitySettings": {
      "show": false,
      "xver": 0,
      "target": "ya.ru:443",
      "serverNames": ["ya.ru"],
      "shortIds": ["cb2413b8", "..."],
      "settings": {
        "publicKey": "...",
        "fingerprint": "chrome",
        "serverName": "ya.ru",
        "spiderX": "/"
      }
    }
  }
}
```

### 5.2 Добавить безопасный JSON loader

Добавить helper:

```python
def _loads_json(self, value, default=None):
    if default is None:
        default = {}
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default
```

### 5.3 Добавить helper `_first`

```python
def _first(self, value, default=""):
    if isinstance(value, list):
        return value[0] if value else default
    return value or default
```

### 5.4 Исправить `get_reality_settings`

Заменить текущую реализацию на устойчивую:

```python
async def get_reality_settings(self) -> dict:
    if self._reality_cache:
        return self._reality_cache

    inbound = await self.get_inbound(config.INBOUND_ID)
    if not inbound:
        logger.error("Failed to get inbound for Reality settings")
        return {}

    try:
        stream_settings_raw = (
            inbound.get("streamSettings")
            or inbound.get("stream_settings")
            or "{}"
        )
        inbound_settings_raw = inbound.get("settings") or "{}"

        stream_settings = self._loads_json(stream_settings_raw, {})
        inbound_settings = self._loads_json(inbound_settings_raw, {})

        reality = stream_settings.get("realitySettings", {})
        reality_nested = reality.get("settings", {})

        clients = inbound_settings.get("clients", [])
        first_client_flow = ""
        if clients:
            first_client_flow = next(
                (client.get("flow", "") for client in clients if client.get("flow")),
                ""
            )

        public_key = (
            reality.get("publicKey")
            or reality_nested.get("publicKey")
            or config.REALITY_PUBLIC_KEY
            or ""
        )

        sni = (
            reality_nested.get("serverName")
            or self._first(reality.get("serverNames"), "")
            or self._first(reality_nested.get("serverNames"), "")
            or config.REALITY_SNI
            or config.XUI_SERVER_NAME
            or ""
        )

        short_id = (
            self._first(reality.get("shortIds"), "")
            or reality_nested.get("shortId")
            or self._first(reality_nested.get("shortIds"), "")
            or config.REALITY_SHORT_ID
            or ""
        )

        spider_x = (
            reality_nested.get("spiderX")
            or reality.get("spiderX")
            or config.REALITY_SPIDER_X
            or "/"
        )

        fingerprint = (
            reality_nested.get("fingerprint")
            or reality.get("fingerprint")
            or config.REALITY_FINGERPRINT
            or "chrome"
        )

        flow = (
            first_client_flow
            or reality_nested.get("flow")
            or reality.get("flow")
            or "xtls-rprx-vision"
        )

        port = inbound.get("port", 443)

        missing = []
        if not public_key:
            missing.append("public_key")
        if not sni:
            missing.append("sni")
        if not short_id:
            missing.append("short_id")

        if missing:
            logger.error(f"Reality settings incomplete. Missing: {', '.join(missing)}")
            return {}

        self._reality_cache = {
            "public_key": public_key,
            "sni": sni,
            "short_id": short_id,
            "spider_x": spider_x,
            "fingerprint": fingerprint,
            "flow": flow,
            "port": port,
        }

        logger.info(
            "Reality settings loaded: "
            f"sni={sni}, sid={short_id}, fp={fingerprint}, "
            f"spx={spider_x}, flow={flow}, port={port}"
        )

        return self._reality_cache

    except Exception as e:
        logger.exception(f"Failed to parse Reality settings: {e}")
        return {}
```

### 5.5 Исправить создание клиента

В `create_vless_profile()` при создании `new_client`:

#### Требования

- `flow` должен быть `xtls-rprx-vision`.
- Не добавлять в client лишние Reality-поля, если 3x-ui 3.4.x их не хранит в клиенте.
- Минимально совместимый client для VLESS Reality:

```python
new_client = {
    "id": client_id,
    "flow": reality.get("flow", "xtls-rprx-vision"),
    "email": email,
    "limitIp": 0,
    "totalGB": 0,
    "expiryTime": expiry_time * 1000,
    "enable": True,
    "tgId": telegram_id,
    "subId": sub_id,
    "reset": 0,
}
```

#### Важно

Сейчас в базе есть старые клиенты с полями:

```json
"auth"
"password"
"security"
"group"
```

Для новых клиентов бота эти поля не нужны, если 3x-ui API принимает обычный VLESS client.

Если API update inbound начинает ломаться из-за отсутствия новых 3.4.x полей `created_at` / `updated_at`, добавить:

```python
now_ms = int(datetime.utcnow().timestamp() * 1000)

new_client["created_at"] = now_ms
new_client["updated_at"] = now_ms
```

### 5.6 Возвращаемый `profile_data`

В `create_vless_profile()` вернуть:

```python
return {
    "client_id": client_id,
    "email": email,
    "port": reality.get("port", inbound.get("port", 443)),
    "security": "reality",
    "remark": inbound["remark"],
    "sni": reality["sni"],
    "pbk": reality["public_key"],
    "fp": reality.get("fingerprint", "chrome"),
    "sid": reality["short_id"],
    "spx": reality.get("spider_x", "/"),
    "flow": reality.get("flow", "xtls-rprx-vision"),
    "sub_id": sub_id,
}
```

### 5.7 Исправить `generate_vless_url`

Заменить функцию так, чтобы URL был формата:

```text
vless://UUID@vless.frostbite-rogueite22768.my-vm.work:30443?type=tcp&security=reality&pbk=PUBLIC_KEY&fp=chrome&sni=ya.ru&sid=SHORT_ID&spx=%2F&flow=xtls-rprx-vision&encryption=none#remark-email
```

Реализация:

```python
from urllib.parse import urlencode, quote
```

```python
def generate_vless_url(profile_data: dict) -> str:
    remark = profile_data.get("remark", "")
    email = profile_data["email"]
    fragment = f"{remark}-{email}" if remark else email

    query = {
        "type": "tcp",
        "security": "reality",
        "pbk": profile_data.get("pbk", ""),
        "fp": profile_data.get("fp", "chrome"),
        "sni": profile_data.get("sni", ""),
        "sid": profile_data.get("sid", ""),
        "spx": profile_data.get("spx", "/"),
        "flow": profile_data.get("flow", "xtls-rprx-vision"),
        "encryption": "none",
    }

    return (
        f"vless://{profile_data['client_id']}@{config.XUI_HOST}:{profile_data['port']}"
        f"?{urlencode(query)}"
        f"#{quote(fragment)}"
    )
```

### 5.8 Исправить `generate_sub_url`

Текущая логика не подходит для кастомного path.

Реализация:

```python
from urllib.parse import urlparse
```

```python
def generate_sub_url(sub_id: str) -> str:
    sub_path = (config.XUI_SUB_PATH or "/sub/").strip()

    if not sub_path.startswith("/"):
        sub_path = f"/{sub_path}"

    if not sub_path.endswith("/"):
        sub_path = f"{sub_path}/"

    if not config.SUBSCRIPTION_URL_BASE:
        parsed = urlparse(config.XUI_API_URL)
        scheme = parsed.scheme or "http"
        host = parsed.hostname or "localhost"
        port = f":{config.XUI_SUB_PORT}" if config.XUI_SUB_PORT else ""
        return f"{scheme}://{host}{port}{sub_path}{sub_id}"

    return f"{config.SUBSCRIPTION_URL_BASE.rstrip('/')}{sub_path}{sub_id}"
```

Ожидаемый результат:

```text
https://panel.frostbite-rogueite22768.my-vm.work:20576/frostbite-sub-8q2m7k/<subId>
```

---

## 6. API path и BasicAuth

### 6.1 Внутри Docker

Если:

```env
XUI_API_URL=http://3x-ui-allinone:21443
```

то:

- `XUI_VERIFY_SSL=False`;
- `NGINX_BASIC_AUTH_USER` пустой;
- `NGINX_BASIC_AUTH_PASSWORD` пустой;
- BasicAuth не нужен.

### 6.2 Снаружи Docker

Если используется внешний URL:

```env
XUI_API_URL=https://panel.frostbite-rogueite22768.my-vm.work:20576
```

тогда:

- `XUI_VERIFY_SSL=True`;
- нужны `NGINX_BASIC_AUTH_USER`;
- нужны `NGINX_BASIC_AUTH_PASSWORD`;
- IP контейнера/хоста должен быть в allowlist.

Основной production-вариант — внутренний Docker URL.

---

## 7. Dockerfile для бота

Создать в корне репозитория бота:

```text
Dockerfile
```

Пример:

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip wheel \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY templates /app/templates

WORKDIR /app/src

CMD ["python", "app.py"]
```

---

## 8. `.dockerignore`

Создать:

```dockerignore
.git
.venv
__pycache__
*.pyc
users.db
*.db
*.sqlite
.env
src/.env
data
logs
```

---

## 9. Compose-сервис бота

Есть два варианта.

### Вариант A: добавить сервис в `3x-ui-deploy-sq/compose.yml`

Добавить рядом с `3x-ui-allinone`:

```yaml
  frostbite-tg-client-bot:
    build:
      context: ../3x-ui-tg-client-pay
      dockerfile: Dockerfile
    container_name: frostbite-tg-client-bot
    restart: unless-stopped
    env_file:
      - ../3x-ui-tg-client-pay/src/.env
    depends_on:
      - 3x-ui-allinone
    volumes:
      - ../3x-ui-tg-client-pay/data:/app/data
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp:size=64m,noexec,nosuid,nodev
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Плюс создать директорию:

```bash
mkdir -p ../3x-ui-tg-client-pay/data
```

### Вариант B: отдельный compose у бота и external network

Если не хочется менять compose панели:

1. Узнать имя сети:

```bash
docker inspect 3x-ui-allinone --format '{{json .NetworkSettings.Networks}}'
```

2. В compose бота:

```yaml
services:
  frostbite-tg-client-bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: frostbite-tg-client-bot
    restart: unless-stopped
    env_file:
      - ./src/.env
    networks:
      - frostbite_net
    volumes:
      - ./data:/app/data
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp:size=64m,noexec,nosuid,nodev
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

networks:
  frostbite_net:
    external: true
    name: <ACTUAL_3X_UI_DOCKER_NETWORK>
```

Предпочтительный вариант — A, если проекты лежат рядом:

```text
~/.openclaw/workspace/
├── 3x-ui-deploy-sq
└── 3x-ui-tg-client-pay
```

---

## 10. Healthcheck / diagnostics

Добавить файл:

```text
src/check_xui.py
```

Назначение:

- проверить логин;
- получить inbound `INBOUND_ID`;
- вывести remark/port/protocol;
- распарсить Reality settings;
- вывести безопасный summary.

Пример:

```python
import asyncio
from functions import XUIAPI
from config import config


async def main():
    api = XUIAPI()
    try:
        ok = await api.login()
        print(f"login={ok}")

        inbound = await api.get_inbound(config.INBOUND_ID)
        print(f"inbound_exists={bool(inbound)}")

        if inbound:
            print(f"id={inbound.get('id')}")
            print(f"remark={inbound.get('remark')}")
            print(f"port={inbound.get('port')}")
            print(f"protocol={inbound.get('protocol')}")

        reality = await api.get_reality_settings()
        safe = dict(reality)
        if safe.get("public_key"):
            safe["public_key"] = safe["public_key"][:8] + "***"
        if safe.get("short_id"):
            safe["short_id"] = safe["short_id"][:2] + "***"
        print(f"reality={safe}")

    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
```

Запуск:

```bash
docker compose exec frostbite-tg-client-bot python check_xui.py
```

---

## 11. Тест-план

### 11.1 Проверка сборки

```bash
docker compose build frostbite-tg-client-bot
```

### 11.2 Проверка запуска

```bash
docker compose up -d frostbite-tg-client-bot
docker logs -f frostbite-tg-client-bot
```

Ожидаемо:

```text
Database initialized
Admin status updated
Bot commands registered successfully
Handlers registered
Starting bot...
```

### 11.3 Проверка API из контейнера

```bash
docker compose exec frostbite-tg-client-bot python check_xui.py
```

Ожидаемо:

```text
login=True
inbound_exists=True
id=3
remark=VLESS\Reality
port=30443
protocol=vless
flow=xtls-rprx-vision
sni=ya.ru
fingerprint=chrome
```

### 11.4 Проверка создания тестового клиента

Через Telegram:

```text
/start
/connect
```

или через админ-функцию, если есть.

Проверить в 3x-ui:

```bash
sqlite3 -header -json data/x-ui/x-ui.db \
'select settings from inbounds where id = 3;'
```

У нового клиента должно быть:

```json
"flow": "xtls-rprx-vision"
```

### 11.5 Проверка VLESS URL

Ссылка должна содержать:

```text
@vless.frostbite-rogueite22768.my-vm.work:30443
type=tcp
security=reality
pbk=
fp=chrome
sni=ya.ru
sid=
spx=%2F
flow=xtls-rprx-vision
encryption=none
```

### 11.6 Проверка subscription URL

Ссылка должна быть:

```text
https://panel.frostbite-rogueite22768.my-vm.work:20576/frostbite-sub-8q2m7k/<subId>
```

---

## 12. Безопасность

### 12.1 Не коммитить секреты

Не коммитить:

```text
src/.env
users.db
data/
*.db
bot token
payment token
3x-ui password
Reality privateKey
```

### 12.2 Reality private key

В процессе диагностики был выведен Reality `privateKey`.

После завершения интеграции желательно:

1. Пересоздать Reality keypair в 3x-ui.
2. Обновить inbound.
3. Перегенерировать клиентские ссылки.

---

## 13. Дополнительные cleanup-задачи

### 13.1 Убрать duplicate port mapping в compose панели

В текущем compose есть дубль:

```yaml
- "127.0.0.1:21443:21443/tcp"
- "127.0.0.1:21443:21443/tcp"
```

Оставить одну строку.

### 13.2 Проверить Dockerfile панели

В README старое упоминание `v3.2.5`, фактически используется `v3.4.2`.

Обновить README/документацию, если нужно.

---

## 14. Критерии готовности

Задача считается выполненной, если:

- бот собирается в Docker;
- бот запускается через compose;
- бот подключается к `3x-ui-allinone:21443`;
- бот успешно логинится в 3x-ui API;
- бот получает inbound `id=3`;
- бот корректно парсит Reality settings 3x-ui 3.4.2;
- новый клиент создаётся в inbound `id=3`;
- новый клиент имеет `flow=xtls-rprx-vision`;
- VLESS URL содержит корректные Reality параметры;
- subscription URL содержит `/frostbite-sub-8q2m7k/`;
- наружу у контейнера бота нет открытых портов;
- секреты не попадают в git.

---

## 15. Рекомендуемая последовательность разработки

1. Обновить `config.py`.
2. Обновить `.env.example`.
3. Обновить `functions.py`:
   - JSON helpers;
   - Reality parser;
   - VLESS URL generator;
   - subscription URL generator.
4. Добавить `check_xui.py`.
5. Добавить Dockerfile.
6. Добавить `.dockerignore`.
7. Добавить compose-сервис.
8. Прогнать локальный syntax check.
9. Собрать контейнер.
10. Проверить API из контейнера.
11. Создать тестового клиента.
12. Проверить ссылку и подписку.
13. Очистить тестового клиента.
14. Зафиксировать изменения в git.
