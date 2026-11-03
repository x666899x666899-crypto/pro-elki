"""Проверка фраз без Telegram и без настоящей таблицы."""

from datetime import datetime, timedelta, timezone

from catalog import parse_csv, parse_stock
from talk import ADDRESS, GREETING, HANDOFF, NIGHT, NO_PRICE, NO_STOCK, ORDER, SITE, answer

ULAN_UDE = timezone(timedelta(hours=8))
DAY = datetime(2026, 10, 31, 14, 0, tzinfo=ULAN_UDE)
NIGHT_HOUR = datetime(2026, 10, 31, 23, 30, tzinfo=ULAN_UDE)
TREE = [
    {"name": "Ёлка литая 180", "price": "5 000", "stock": 4, "category": "Елки и елочки"},
    {"name": "Ёлка литая 210", "price": "7 000", "stock": 0, "category": "Елки и елочки"},
]


def test_greeting_address_delivery_site():
    assert GREETING in answer("/start", TREE, DAY).texts[0]
    for phrase in ("привет", "здравствуйте", "добрый день", "здорово", "дарова", "хай", "hello", "hi"):
        assert answer(phrase, TREE, DAY).texts == [GREETING], phrase
    assert answer("привет, как проехать?", TREE, DAY).texts == [ADDRESS]
    assert "Цена" in answer("привет, сколько стоит елка 180", TREE, DAY).texts[0]
    assert answer("где вы находитесь", TREE, DAY).texts == [ADDRESS]
    for phrase in (
        "как проехать к вам?",
        "как пройти",
        "как к вам пройти",
        "на каком автобусе доехать",
        "где находитесь",
        "до скольки работаете",
        "когда закроетесь",
        "час ещё будете на месте",
    ):
        assert answer(phrase, TREE, DAY).texts == [ADDRESS], phrase
    price = answer("до скольки стоит елка 180", TREE, DAY)
    assert "Цена" in price.texts[0]
    assert "такси" in answer("есть доставка?", TREE, DAY).texts[0]
    assert answer("хочу посмотреть ассортимент", TREE, DAY).texts == [SITE]


def test_price_and_stock():
    found = answer("сколько стоит елка 180", TREE, DAY)
    assert found.texts == ["🎄 Ёлка литая 180\n\n💰 Цена: 5 000 ₽\n✅ Да, есть в наличии."]
    assert found.handoff is None
    assert "4" not in found.texts[0]
    short = answer("елка 180 три штуки", [{"name": "Ёлка литая 180", "price": "5 000", "stock": 2, "category": ""}], DAY)
    assert short.texts == [NO_STOCK]
    empty = answer("сколько стоит елка 210", TREE, DAY)
    assert empty.texts == [NO_STOCK]
    missing = answer("сколько стоит гирлянда лунная", TREE, DAY)
    assert missing.texts == [NO_PRICE]


def test_without_sheet_and_unclear():
    assert answer("сколько стоит елка", None, DAY).texts == [NO_PRICE]
    assert answer("абракадабра", TREE, DAY).texts == [HANDOFF]
    order = answer("хочу оформить заказ", TREE, DAY)
    assert order.texts == [ORDER]
    assert order.handoff == "buy"
    assert answer("где мой заказ", TREE, DAY).texts == [HANDOFF]


def test_night():
    assert answer("сколько стоит елка 180", TREE, NIGHT_HOUR).texts == [NIGHT]


def test_csv_ignores_rows_without_price():
    text = "Категория,Наименование,Артикул,Цена продажи опт,Цена продажи розница,Остаток\nЕлки,Ёлка литая 180,У14,1000,5000,3\nЕлки,Без цены,У15,100,,1\n"
    items, note = parse_csv(text)
    assert note == ""
    assert len(items) == 1
    assert items[0]["price"] == "5000"
    assert items[0]["stock"] == 3
    wholesale_only, missing = parse_csv("Наименование,Цена продажи опт\nЁлка,100\n")
    assert wholesale_only == []
    assert "цены" in missing
    assert parse_stock("без ограничения") == "unlimited"
    assert parse_stock("") is None


if __name__ == "__main__":
    test_greeting_address_delivery_site()
    test_price_and_stock()
    test_without_sheet_and_unclear()
    test_night()
    test_csv_ignores_rows_without_price()
    print("фразы сошлись")
