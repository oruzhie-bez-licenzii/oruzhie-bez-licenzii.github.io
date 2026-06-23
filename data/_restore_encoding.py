# -*- coding: utf-8 -*-
"""Восстановление кодировки products.json.

Повреждение №1 (основное): исходный UTF-8 был прочитан как CP1251 и снова
сохранён в UTF-8 (двойная перекодировка). Обратное: s.encode(cp1251).decode utf-8.

Повреждение №2: прошлый скрипт «схлопнул» типографские кавычки в простой
апостроф '(U+0027). В мойибейке это второй байт буквы:
  С' -> ё (байт 0x91)
  Р' -> Б (0x91) или В (0x92) — определяется по контексту слова.

Детектор мойибейка — по «чистоте» результата (меньше латин-1/редких символов),
поэтому ловит и капс-имена (АК-74М), и цены (₽), не трогая чистый текст и ASCII.
"""
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# карта: unicode-символ -> байт cp1251 (+ passthrough undefined 0x98)
REV = {}
for b in range(256):
    try:
        REV[bytes([b]).decode('cp1251')] = b
    except Exception:
        pass
REV['\x98'] = 0x98


def _decode_window(s):
    """Грубо реверсим кусок мойибейка для анализа контекста (апостроф->В)."""
    out = bytearray()
    for ch in s:
        out.append(0x92 if ch == "'" else REV.get(ch, 0x3f))
    return out.decode('utf-8', errors='ignore')


def _resolve_d0(s, i):
    """Апостроф на позиции i, перед ним 'Р' (лид-байт D0): вернуть 0x91(Б)/0x92(В)."""
    tail = _decode_window(s[i + 1:i + 16])
    head = _decode_window(s[max(0, i - 8):i - 1])  # текст до текущей буквы
    if tail[:2] == 'ое':            # Боевой, Боеприпасы
        return 0x91
    if tail.startswith('есшум'):    # Бесшумный
        return 0x91
    if tail.startswith('раун'):     # Браунинг
        return 0x91
    if tail.startswith('П)'):       # бронебойные (БП)
        return 0x91
    if head[-1:] in ('П', 'Г') and (tail[:1] in (' ', ',', '.', '(', ')', '')):
        return 0x91                 # ПБ, КГБ — аббревиатуры, оканч. на Б
    return 0x92                     # по умолчанию В


def try_fix(s):
    """Вернуть восстановленную строку или None."""
    out = bytearray()
    for i, ch in enumerate(s):
        if ch == "'":
            prev = out[-1] if out else None
            if prev == 0xD1:        # С' -> ё
                out.append(0x91)
            elif prev == 0xD0:      # Р' -> Б/В
                out.append(_resolve_d0(s, i))
            else:                   # настоящий апостроф
                out.append(0x27)
        elif ch in REV:
            out.append(REV[ch])
        else:
            return None
    try:
        return out.decode('utf-8')
    except UnicodeDecodeError:
        return None


_GOOD_EXTRA = set('₽—–×№…«»„“” •')


def _bad_count(s):
    """Кол-во 'подозрительных' символов (артефакты мойибейка)."""
    n = 0
    for c in s:
        o = ord(c)
        if c.isascii() and (c.isprintable() or c in '\n\t'):
            continue
        if 'а' <= c <= 'я' or 'А' <= c <= 'Я' or c in 'ёЁ':
            continue
        if c in _GOOD_EXTRA:
            continue
        n += 1
    return n


def smart(s):
    f = try_fix(s)
    # применяем фикс только если результат «чище» исходника — защита чистого текста
    if f is not None and f != s and _bad_count(f) < _bad_count(s):
        return f
    return s


def walk(o):
    if isinstance(o, str):
        return smart(o)
    if isinstance(o, dict):
        return {k: walk(v) for k, v in o.items()}
    if isinstance(o, list):
        return [walk(v) for v in o]
    return o


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else 'products.json.bak'
    dst = sys.argv[2] if len(sys.argv) > 2 else 'products.json'
    data = json.load(open(src, encoding='utf-8-sig'))
    fixed = walk(data)

    suspicious = []

    def check(o, path=''):
        if isinstance(o, str):
            if _bad_count(o) > 0 or (try_fix(o) and try_fix(o) != o and _bad_count(try_fix(o)) < _bad_count(o)):
                suspicious.append((path, o[:70]))
        elif isinstance(o, dict):
            for k, v in o.items():
                check(v, path + '/' + str(k))
        elif isinstance(o, list):
            for j, v in enumerate(o):
                check(v, path + '[' + str(j) + ']')

    check(fixed)

    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(fixed, f, ensure_ascii=False, indent=2)

    print('Записано:', dst)
    print('Остаточных подозрительных строк:', len(suspicious))
    for p, s in suspicious[:30]:
        print('  ', p, '::', repr(s))


if __name__ == '__main__':
    main()
