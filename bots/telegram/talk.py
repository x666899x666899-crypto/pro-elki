"""Ответы покупателю по сценарию. Цену подставляет только найденная строка таблицы."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

GREETING = (
    "🎄 Добрый день!\n\n"
    "На связи магазин «ПРО ЁЛКИ», менеджер Валентина.\n\n"
    "Очень рады, что вы к нам обратились. Сейчас подскажу и помогу ответить на вопросы.\n\n"
    "Что вас интересует?\n"
    "Уже подобрали что-то из ассортимента или нужна помощь?\n\n"
    "У нас много новогодней красоты:\n"
    "для дома, для улицы и подарки."
)
ADDRESS = (
    "📍 Наш адрес\n\n"
    "г. Улан-Удэ\n"
    "ул. Ботаническая, 37\n"
    "база «Сезар», павильон 9\n\n"
    "🕐 Работаем\n"
    "с 11:00 до 22:00, без выходных\n\n"
    "📞 Позвонить\n"
    "+79025348081\n\n"
    "🚏 Как добраться\n"
    "Остановка «Тумэр Морин»\n"
    "Автобус 3к, маршрутка 33 и 57\n"
    "Трамвай 1, 2 и 5, остановка рядом\n\n"
    "🗺 Маршрут\n"
    "2ГИС:\n"
    "https://2gis.ru/ulanude/directions/points/%7C107.648385%2C51.841217%3B70000001081652905\n\n"
    "Яндекс Карты:\n"
    "https://yandex.ru/maps/org/sezar/25466638696/?mode=routes\n\n"
    "🌐 Сайт\n"
    "https://proelki03.ru/\n\n"
    "💬 Если удобнее написать в MAX:\n"
    "https://max.ru/u/f9LHodD0cOK6kULKP16FxmzpzVz3oNPdwg1uEciq9wvldICbrQREk6Yqk6s\n\n"
    "📣 Наша группа в Telegram:\n"
    "https://t.me/proproelki"
)
DELIVERY = (
    "🚕 Доставка\n\n"
    "По городу есть, по тарифу такси.\n\n"
    "Чтобы назвать стоимость, напишите:\n"
    "что везти и куда везти."
)
SITE = (
    "🌐 Ассортимент\n\n"
    "Посмотреть можно на сайте:\n"
    "https://proelki03.ru/"
)
HANDOFF = "💬 Сейчас передам диалог Валентине."
NO_PRICE = (
    "💬 В списке нет точной цены.\n\n"
    "Сейчас передам диалог Валентине, она проверит."
)
NO_STOCK = (
    "📦 Сейчас уточню наличие и передам диалог.\n\n"
    "Вам ответит человек."
)
NIGHT = (
    "🌙 Сейчас мы немного отдыхаем.\n\n"
    "Поспим пару часов и с утра ответим на ваш вопрос.\n\n"
    "Доброй ночи."
)
ORDER = (
    "💬 Сейчас передам диалог Валентине.\n\n"
    "🛍 Чтобы оформить заказ, перейдите на сайт:\n"
    "https://proelki03.ru/"
)

# Утро в переписке Сергей не назвал. До его правки тихий час совпадает с открытием зала.
QUIET_FROM = 23
QUIET_UNTIL = 11

WORDS = {
    "один": 1,
    "одну": 1,
    "одна": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
}
STOP = {
    "сколько", "скольки", "стоит", "стоят", "цена", "цену", "цены", "стоимость", "есть", "ли",
    "еще", "сегодня", "сейчас", "вам", "вас", "ваш", "ваша", "наши", "наш", "магазин",
    "привет", "приветик", "здравствуйте", "здравствуй", "здрасте", "здрасьте",
    "здорово", "здоров", "дарова", "даров", "здарова", "здаров", "хай", "hello", "hey", "салют",
    "добрый", "день", "вечер", "утро",
    "в", "во", "на", "по", "и", "или", "а", "это", "что", "как", "меня", "мне",
    "подскажите", "пожалуйста", "хочу", "нужен", "нужна", "нужно", "нужны",
    "какой", "какая", "какие", "какое", "наличие", "наличии", "скажите",
    "можно", "узнать", "интересно", "интересует", "товар", "позиция",
    "см", "метр", "метра", "метров", "штук", "штуки", "штука", "штуку",
}
CATEGORIES = {
    "елки", "елочка", "елочки", "игрушки", "игрушка", "гирлянды", "гирлянда",
    "декор", "подарки", "подарок", "упаковка",
}
PRODUCT_STEMS = ("елк", "гирлянд", "игруш", "декор", "подарок", "упаков", "ель", "пихт", "кедр")


@dataclass
class Reply:
    texts: list[str]
    handoff: str | None = None


def answer(text: str, items: list[dict] | None, now: datetime) -> Reply:
    if _quiet(now):
        return Reply([NIGHT])
    raw = (text or "").strip()
    if not raw:
        return Reply([HANDOFF], "unclear")
    norm = _norm(raw)
    if norm.startswith("/start") or _greeting_only(norm):
        return Reply([GREETING])
    if _about_place(norm):
        return Reply([ADDRESS])
    if "достав" in norm:
        return Reply([DELIVERY])
    if _has(norm, ("сайт", "ассортимент", "каталог", "не определ", "посмотреть")):
        return Reply([SITE])
    if "где" in norm and "заказ" in norm:
        return Reply([HANDOFF], "order-status")
    price_intent = _has(norm, ("цена", "стоит", "стоимость", "налич"))
    buy_intent = _has(norm, ("купит", "купить", "оформить", "закажу", "заказ", "беру", "готов"))
    if price_intent or _looks_like_product(norm):
        found = _price_reply(norm, items)
        if buy_intent and found.handoff is None:
            found.texts.append(ORDER)
            found.handoff = "buy"
        return found
    if buy_intent:
        return Reply([ORDER], "buy")
    return Reply([HANDOFF], "unclear")


def _price_reply(norm: str, items: list[dict] | None) -> Reply:
    if not items:
        return Reply([NO_PRICE], "no-price")
    words = _product_words(norm)
    if words and set(words) <= CATEGORIES and not _has(norm, ("стоит", "цена", "стоимость")):
        return Reply([SITE])
    if not words:
        return Reply([HANDOFF], "unclear")
    scored = []
    for item in items:
        name = _norm(f"{item['name']} {item.get('article') or ''}")
        score = sum(1 for word in words if word in name)
        if score:
            scored.append((score, len(words), item))
    if not scored:
        return Reply([NO_PRICE], "no-price")
    best = max(row[0] for row in scored)
    top = [row[2] for row in scored if row[0] == best]
    if len(top) != 1 or best < len(words):
        return Reply([HANDOFF], "unclear")
    item = top[0]
    need = _quantity(norm)
    stock = item.get("stock")
    if stock is None:
        return Reply([NO_STOCK], "stock")
    if stock != "unlimited" and (stock <= 0 or (need and stock < need)):
        return Reply([NO_STOCK], "stock")
    price = item["price"].strip()
    if "₽" not in price and "руб" not in price.lower():
        price = f"{price} ₽"
    return Reply([f"🎄 {item['name']}\n\n💰 Цена: {price}\n✅ Да, есть в наличии."])


def _quantity(norm: str):
    match = re.search(r"(\d+)\s*шт", norm)
    if match:
        return int(match.group(1))
    for word, number in WORDS.items():
        if re.search(rf"\b{word}\b", norm) and "шт" in norm:
            return number
    return None


def _about_place(norm: str) -> bool:
    """Адрес, дорога и часы работы. Это не повод звать Валентину."""
    if _has(norm, ("стоит", "цена", "стоимость", "налич")) and not _has(
        norm, ("работ", "открыт", "закры", "адрес", "проех", "доеха", "добрат")
    ):
        return False
    if _has(norm, ("будете", "будешь")) and _has(norm, ("час", "еще", "месте", "работ", "открыт")):
        return True
    if _has(norm, ("открыт", "закрыт", "работ")) and not _looks_like_product(norm):
        return True
    return _has(
        norm,
        (
            "адрес",
            "где вы",
            "где наход",
            "где магазин",
            "где вас",
            "как добрат",
            "как доеха",
            "как проех",
            "как пройти",
            "как попаст",
            "как найти",
            "пройти",
            "пешком",
            "дойти",
            "проехат",
            "доехат",
            "добрат",
            "подъехат",
            "автобус",
            "трамвай",
            "маршрутк",
            "остановк",
            "маршрут",
            "график",
            "режим",
            "часы",
            "до скольк",
            "до которого",
            "во сколько",
            "когда закры",
            "когда откр",
            "закро",
            "откроет",
            "на месте",
            "успею",
            "телефон",
            "позвон",
            "павильон",
            "сезар",
            "ботаническ",
        ),
    )


def _looks_like_product(norm: str) -> bool:
    words = _product_words(norm)
    if any(word in CATEGORIES or any(word.startswith(stem) for stem in PRODUCT_STEMS) for word in words):
        return True
    return bool(re.search(r"\b\d{2,3}\b", norm)) and bool(words)


def _product_words(norm: str) -> list[str]:
    words = []
    for word in re.findall(r"[a-zа-я0-9]+", norm):
        if word in STOP or word in WORDS or len(word) < 3:
            continue
        if word.isdigit():
            words.append(word)
            continue
        words.append(word)
    return words


def _greeting_only(norm: str) -> bool:
    parts = (
        "добрый день", "добрый вечер", "доброе утро", "доброй ночи",
        "здравствуйте", "здравствуй", "здрасьте", "здрасте",
        "приветик", "привет",
        "здорово", "здоров",
        "здарова", "здаров", "дарова", "даров",
        "хаюшки", "хай", "hello", "hey", "салют", "добрый",
    )
    if not any(part in norm for part in parts) and not re.search(r"\bhi\b", norm):
        return False
    stripped = norm
    for part in parts:
        stripped = stripped.replace(part, " ")
    stripped = re.sub(r"\bhi\b", " ", stripped)
    for filler in ("как дела", "как ты", "как ваши дела", "как сам", "как сами"):
        stripped = stripped.replace(filler, " ")
    if _product_words(stripped):
        return False
    if _has(norm, ("адрес", "достав", "цена", "стоит", "сайт", "заказ", "купит", "проех", "наход", "работ", "закры")):
        return False
    return True


def _quiet(now: datetime) -> bool:
    hour = now.hour
    return hour >= QUIET_FROM or hour < QUIET_UNTIL


def _has(norm: str, parts: tuple[str, ...]) -> bool:
    return any(part in norm for part in parts)


def _norm(value: str) -> str:
    return value.lower().replace("ё", "е").replace("\xa0", " ")
