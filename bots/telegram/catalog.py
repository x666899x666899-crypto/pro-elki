"""Чтение раздела «ёлки» из Google-таблицы.

Бот берёт только тот лист, имя которого передано снаружи. Другие листы,
включая ShopShop, сюда не попадают. Если таблица не открылась или столбцы
не узнаны, товаров нет: бот не выдумывает цену.
"""

from __future__ import annotations

import csv
import io
import re
import urllib.error
import urllib.parse
import urllib.request

NAME_HEADERS = ("название", "наименование", "товар", "позиция", "name")
STOCK_HEADERS = ("остаток", "наличие", "stock")
CATEGORY_HEADERS = ("категория", "раздел", "группа", "category")
ARTICLE_HEADERS = ("артикул", "sku")

UNLIMITED = ("без ограничения", "неограничено", "много", "есть", "в наличии")


def load_sheet(sheet_id: str, sheet_name: str, sheet_gid: str = "", timeout: float = 20) -> tuple[list[dict], str]:
    """Возвращает товары и короткую причину, если список пуст."""
    if not sheet_id.strip():
        return [], "идентификатор таблицы не задан"
    base = (
        "https://docs.google.com/spreadsheets/d/"
        + urllib.parse.quote(sheet_id.strip(), safe="")
        + "/gviz/tq?tqx=out:csv"
    )
    if sheet_gid.strip():
        url = base + "&gid=" + urllib.parse.quote(sheet_gid.strip(), safe="")
    else:
        url = base + "&sheet=" + urllib.parse.quote(sheet_name.strip() or "ёлки")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "proelki-bot"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        return [], f"таблица ответила {error.code}"
    except urllib.error.URLError:
        return [], "таблица не открылась"
    text = raw.decode("utf-8-sig", errors="replace")
    if "<html" in text[:500].lower():
        return [], "таблица закрыта, бот её не видит"
    return parse_csv(text)


def parse_csv(text: str) -> tuple[list[dict], str]:
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [], "лист пустой"
    header_index, columns = _find_header(rows)
    if columns.get("name") is None or columns.get("price") is None:
        return [], "на листе не найдены столбцы названия и цены"
    items = []
    for row in rows[header_index + 1 :]:
        name = _cell(row, columns["name"])
        price = _cell(row, columns["price"])
        if not name or not price:
            continue
        stock = _cell(row, columns["stock"]) if columns.get("stock") is not None else ""
        category = _cell(row, columns["category"]) if columns.get("category") is not None else ""
        article = _cell(row, columns["article"]) if columns.get("article") is not None else ""
        items.append(
            {
                "name": name,
                "article": article,
                "price": price,
                "stock": parse_stock(stock),
                "category": category,
            }
        )
    if not items:
        return [], "на листе нет строк с названием и ценой"
    return items, ""


def parse_stock(value: str):
    text = value.strip().lower().replace("ё", "е")
    if not text:
        return None
    if any(mark in text for mark in UNLIMITED):
        return "unlimited"
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return None
    return int(digits)


def _find_header(rows: list[list[str]]) -> tuple[int, dict]:
    for index, row in enumerate(rows[:15]):
        normalized = [_norm(cell) for cell in row]
        columns = {
            "name": _match(normalized, NAME_HEADERS),
            "price": _retail_price(normalized),
            "stock": _match(normalized, STOCK_HEADERS),
            "category": _match(normalized, CATEGORY_HEADERS),
            "article": _match(normalized, ARTICLE_HEADERS),
        }
        if columns["name"] is not None and columns["price"] is not None:
            return index, columns
    return 0, {}


def _retail_price(headers: list[str]):
    """Только цена для покупателя. Опт, закуп и приход не берём."""
    for index, header in enumerate(headers):
        if not header or any(word in header for word in ("опт", "закуп", "приход", "себес")):
            continue
        if "розниц" in header or "цена продажи" in header:
            return index
    return None


def _match(headers: list[str], options: tuple[str, ...]):
    for option in options:
        for index, header in enumerate(headers):
            if header == option or header.startswith(option):
                return index
    return None


def _cell(row: list[str], index: int) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def _norm(value: str) -> str:
    return value.strip().lower().replace("ё", "е")
