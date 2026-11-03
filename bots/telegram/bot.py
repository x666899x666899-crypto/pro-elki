"""Слушает @proelki03bot и отвечает по сценарию.

Ключ читается из файла .env рядом с этой программой. В документы он не пишется.
Пока компьютер выключен или спит, программа тоже спит.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from catalog import load_sheet
from talk import answer

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ENV_PATH = ROOT / ".env"
ROUTES = DATA / "routes.json"
OFFSET = DATA / "offset.txt"
ULAN_UDE = timezone(timedelta(hours=8))
CATALOG_PAUSE = 300


def main() -> None:
    env = _env(ENV_PATH)
    token = env.get("BOT_TOKEN", "").strip()
    if not token:
        print("В файле .env нет BOT_TOKEN. Бот не запущен.")
        sys.exit(1)
    me = _api(token, "getMe")
    if not me.get("ok"):
        print("Telegram не принял ключ. Нужен новый ключ в .env, в чат его не присылать.")
        sys.exit(1)
    name = me["result"].get("username", "")
    if name != "proelki03bot":
        print(f"Ключ от другого бота: {name}. Этот запуск остановлен.")
        sys.exit(1)
    _api(token, "deleteWebhook")
    print("Бот слушает сообщения.")
    items: list[dict] = []
    loaded_at = 0.0
    sheet_note = "таблица ещё не проверялась"
    offset = _load_offset()
    while True:
        now_ts = time.time()
        if now_ts - loaded_at >= CATALOG_PAUSE:
            items, sheet_note = load_sheet(
                env.get("SHEET_ID", ""),
                env.get("SHEET_NAME", "ёлки"),
                env.get("SHEET_GID", ""),
            )
            loaded_at = now_ts
            if items:
                print(f"В таблице строк с ценой: {len(items)}")
            else:
                print(f"Цены пока не читаются: {sheet_note}")
        try:
            updates = _api(token, "getUpdates", offset=offset or "", timeout=30)
        except Exception as error:
            print(f"Связь с Telegram прервалась: {error}")
            time.sleep(5)
            continue
        if not updates.get("ok"):
            print("Telegram не отдал сообщения. Повтор через несколько секунд.")
            time.sleep(5)
            continue
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            _save_offset(offset)
            _handle(token, env, update, items)


def _handle(token: str, env: dict, update: dict, items: list[dict]) -> None:
    member = update.get("my_chat_member")
    if member:
        _remember_group(token, env, member.get("chat") or {}, (member.get("new_chat_member") or {}).get("status", ""))
        return
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    kind = chat.get("type")
    if kind in ("group", "supergroup"):
        _from_group(token, env, message)
        return
    if kind != "private" or message.get("from", {}).get("is_bot"):
        return
    text = message.get("text")
    if not text:
        return
    reply = answer(text, items, datetime.now(ULAN_UDE))
    _send(token, chat["id"], reply.texts)
    if reply.handoff:
        _handoff(token, env, chat, message.get("from") or {}, text, reply.handoff)


def _from_group(token: str, env: dict, message: dict) -> None:
    if message.get("from", {}).get("is_bot"):
        return
    chat = message.get("chat") or {}
    routes = _routes(env)
    if not routes.get("group_id"):
        _remember_group(token, env, chat, "member")
        routes = _routes(env)
    reply = message.get("reply_to_message") or {}
    customer = routes.get("by_message", {}).get(str(reply.get("message_id", "")))
    if not customer:
        return
    staff_message = str(message.get("message_id", ""))
    forwarded = routes.setdefault("forwarded", [])
    if staff_message in forwarded:
        return
    forwarded.append(staff_message)
    routes["forwarded"] = forwarded[-200:]
    _save_routes(routes)
    text = (message.get("text") or "").strip()
    if not text:
        _send(token, chat["id"], ["Пока могу переслать покупателю только текст."])
        return
    who = (message.get("from") or {}).get("first_name") or "Менеджер"
    _send(token, customer, [f"{who}: {text}"])
    _send(token, chat["id"], ["Отправил покупателю."])


def _remember_group(token: str, env: dict, chat: dict, status: str) -> None:
    if chat.get("type") not in ("group", "supergroup"):
        return
    if status not in ("member", "administrator", "creator"):
        return
    routes = _routes(env)
    if str(routes.get("group_id")) == str(chat.get("id")):
        return
    routes["group_id"] = chat.get("id")
    _save_routes(routes)
    _send(
        token,
        chat["id"],
        ["Эта группа для заказов и передач. Когда бот не закрыл вопрос, сообщение покупателя появится здесь. Ответьте на него, и ответ уйдёт покупателю."],
    )


def _handoff(token: str, env: dict, chat: dict, person: dict, text: str, reason: str) -> None:
    DATA.mkdir(exist_ok=True)
    record = {
        "time": datetime.now(ULAN_UDE).isoformat(timespec="minutes"),
        "chat_id": chat.get("id"),
        "reason": reason,
        "text": text,
    }
    with (DATA / "handoff.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")
    routes = _routes(env)
    group_id = routes.get("group_id")
    if not group_id:
        return
    who = person.get("first_name") or "покупатель"
    username = person.get("username")
    if username:
        who = f"{who} (@{username})"
    sent = _api(
        token,
        "sendMessage",
        chat_id=group_id,
        text=f"Покупатель написал боту.\n{who}:\n{text}\n\nОтветьте на это сообщение, бот отправит ответ покупателю.",
    )
    message_id = (sent.get("result") or {}).get("message_id")
    if sent.get("ok") and message_id:
        routes.setdefault("by_message", {})[str(message_id)] = chat.get("id")
        _save_routes(routes)


def _routes(env: dict) -> dict:
    routes = {"group_id": None, "by_message": {}}
    if ROUTES.exists():
        try:
            loaded = json.loads(ROUTES.read_text(encoding="utf-8"))
            routes["group_id"] = loaded.get("group_id")
            routes["by_message"] = loaded.get("by_message") or {}
            routes["forwarded"] = loaded.get("forwarded") or []
        except json.JSONDecodeError:
            pass
    if env.get("MANAGER_CHAT_ID", "").strip():
        routes["group_id"] = env["MANAGER_CHAT_ID"].strip()
    return routes


def _save_routes(routes: dict) -> None:
    DATA.mkdir(exist_ok=True)
    stored = {
        "group_id": routes.get("group_id"),
        "by_message": routes.get("by_message") or {},
        "forwarded": routes.get("forwarded") or [],
    }
    ROUTES.write_text(json.dumps(stored, ensure_ascii=False), encoding="utf-8")


def _load_offset():
    if not OFFSET.exists():
        return None
    raw = OFFSET.read_text(encoding="utf-8").strip()
    return int(raw) if raw.isdigit() else None


def _save_offset(offset: int) -> None:
    DATA.mkdir(exist_ok=True)
    OFFSET.write_text(str(offset), encoding="utf-8")


def _send(token: str, chat_id, texts: list[str]) -> None:
    for text in texts:
        if 'href="tel:' in text:
            _api(token, "sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")
        else:
            _api(token, "sendMessage", chat_id=chat_id, text=text)


def _api(token: str, method: str, **params):
    clean = {key: value for key, value in params.items() if value != ""}
    data = urllib.parse.urlencode(clean).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=data,
    )
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        if error.code == 401:
            return {"ok": False}
        raise RuntimeError(body[:200]) from error


def _env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


if __name__ == "__main__":
    main()
