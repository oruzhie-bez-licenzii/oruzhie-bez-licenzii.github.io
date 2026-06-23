# -*- coding: utf-8 -*-
"""Удаляет 5 указанных файлов из photos[] массивов в products.json"""

import json

BAD_FILES = [
    "пистолет-шарк-9ммра-5.jpg",
    "пистолет-гроза-021-9ммра-5.jpg",
    "гроза-051-9ммра-5.jpg",
    "пистолет-wasp-r-9мм-ра-6485-5.jpg",
    "пистолет-shark-9мм-ра-5.jpg",
]

with open("products.json", "r", encoding="utf-8-sig") as f:
    data = json.load(f)

removed_count = 0

for cat in data["categories"]:
    for p in cat.get("products", []):
        photos = p.get("photos", [])
        new_photos = [ph for ph in photos if not any(bad in ph for bad in BAD_FILES)]
        if len(new_photos) != len(photos):
            removed = len(photos) - len(new_photos)
            removed_count += removed
            print(f"  [{p['slug']}]: udaleno {removed} foto ({len(photos)} -> {len(new_photos)})")
            p["photos"] = new_photos

with open("products.json", "w", encoding="utf-8-sig") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nВсего удалено ссылок: {removed_count}")
