# -*- coding: utf-8 -*-
"""Сборщик статического сайта «ТЁМНЫЙ АРСЕНАЛ».
Генерирует HTML-страницы для GitHub Pages.
Запуск: python build.py"""
import json, os, html, shutil, re

def load(f): return json.load(open("data/"+f, encoding="utf-8-sig"))
site = load("site.json")
CATS = load("products.json")["categories"]
CATMAP = {c["slug"]: c for c in CATS}

HEAD   = open("partials/head.html", encoding="utf-8").read()
HEADER = open("partials/header.html", encoding="utf-8").read()
FOOTER = open("partials/footer.html", encoding="utf-8").read()

def e(x): return html.escape(str(x))

# подстановка реквизитов
def fill(t):
    cats_html = '\n'.join(
        '<a href="/%s/">%s</a><br>' % (c["slug"], e(c["name"]))
        for c in CATS)
    dropdown_cats = ''.join(
        '<a href="/%s/">%s</a>' % (c["slug"], e(c["name"]))
        for c in CATS)
    return (t.replace("{{NAME}}", e(site["name"]))
             .replace("{{TAGLINE}}", e(site["tagline"]))
             .replace("{{TAGLINE_SHORT}}", "Боевое оружие с доставкой")
             .replace("{{TG_LINK}}", e(site["tg_link"]))
             .replace("{{TG_PUBLIC}}", e(site["tg_public"]))
             .replace("{{YEAR}}", e(site["year"]))
             .replace("{{CATEGORIES_LIST}}", cats_html)
             .replace("{{DROPDOWN_CATS}}", dropdown_cats))
HEADER_H = fill(HEADER)
FOOTER_H = fill(FOOTER)

URLS = []

def layout(title, desc, path, main_html, keywords="", og_image="", pub_date="", mod_date=""):
    head = (HEAD.replace("{{TITLE}}", title)
                .replace("{{DESCRIPTION}}", desc)
                .replace("{{CANONICAL}}", site["url"] + path)
                .replace("{{KEYWORDS}}", e(keywords)))
    og_title = e(title)
    og_desc = e(desc[:200])
    og_url = site["url"] + path
    og_img = og_image if og_image else site["url"] + "/assets/og-default.jpg"
    head += ('\n<meta property="og:type" content="website">'
             '\n<meta property="og:site_name" content="%s">'
             '\n<meta property="og:title" content="%s">'
             '\n<meta property="og:description" content="%s">'
             '\n<meta property="og:url" content="%s">'
             '\n<meta property="og:image" content="%s">'
             '\n<meta name="twitter:card" content="summary_large_image">'
             '\n<meta name="twitter:title" content="%s">'
             '\n<meta name="twitter:description" content="%s">'
             '\n<meta name="robots" content="index,follow">'
             % (e(site["name"]), og_title, og_desc, og_url, og_img,
                og_title, og_desc))
    # Даты для Яндекса (свежесть контента)
    if pub_date:
        head += '\n<meta name="article:published_time" content="%s">' % pub_date
    if mod_date:
        head += '\n<meta name="article:modified_time" content="%s">' % mod_date
    URLS.append(path)
    return ("<!DOCTYPE html>\n<html lang=\"ru\">\n<head>" + head + "</head>\n<body>\n"
            + HEADER_H + "\n" + main_html + "\n" + FOOTER_H + "\n</body>\n</html>\n")

def write(path, doc):
    d = path.strip("/")
    if d:
        os.makedirs(d, exist_ok=True)
    f = open((d + "/" if d else "") + "index.html", "w", encoding="utf-8-sig")
    f.write(doc)
    f.close()
    print("built", path or "/")

def crumb(name):
    return ('<div class="wrap"><div class="breadcrumb">'
            '<a href="/">Главная</a> / <span>%s</span></div></div>') % e(name)

def crumb2(name1, link1, name2):
    return ('<div class="wrap"><div class="breadcrumb">'
            '<a href="/">Главная</a> / <a href="%s">%s</a> / <span>%s</span></div></div>') % (e(link1), e(name1), e(name2))

def product_img_html(cat, p):
    """Генерирует HTML для изображения товара: img если есть photo, иначе иконка категории."""
    photo = p.get("photo", "")
    if photo:
        return '<img src="%s" alt="%s" loading="lazy">' % (e(photo), e(p["name"]))
    else:
        return '<span class="no-img"></span>'

def product_card(cat, p, show_specs=True):
    """Генерирует карточку товара с изображением."""
    specs = ''
    if show_specs:
        specs = '<ul class="specs"><li><span>Калибр</span><span>%s</span></li><li><span>Тип</span><span>%s</span></li></ul>' % (
            e(p["caliber"]), e(p["type"]))
    return ('<a href="/%s/%s/" class="pcard">'
            '<div class="ph">%s</div>'
            '<div class="pb">'
            '<h3>%s</h3>'
            '%s'
            '<div class="price">%s</div>'
            '<span class="buy">Купить</span>'
            '</div></a>'
            % (e(cat["slug"]), e(p["slug"]),
               product_img_html(cat, p),
               e(p["name"]),
               specs,
               e(p["price"])))

def json_ld_breadcrumb(items):
    item_list = []
    for i, (name, url) in enumerate(items):
        item_list.append('{"@type":"ListItem","position":%d,"name":"%s","item":"%s"}' % (
            i+1, e(name), site["url"] + url))
    return ('<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"BreadcrumbList",'
            '"itemListElement":[%s]}</script>' % ','.join(item_list))

def json_ld_org():
    return ('<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Organization",'
            '"name":"%s","url":"%s",'
            '"contactPoint":[{"@type":"ContactPoint",'
            '"contactType":"sales","url":"%s"}]}</script>'
            % (e(site["name"]), site["url"], site["tg_public"]))

def json_ld_product(p, cat):
    # Изображение товара для JSON-LD (photo уже содержит полный путь /assets/img/products/...)
    photo = p.get("photo", "")
    img_url = ""
    if photo:
        img_url = site["url"] + photo
    # Цена в USD (убираем символы валют)
    price_clean = p["price"].replace("$","").replace("€","").replace("₽","").strip()
    return ('<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"Product",'
            '"name":"%s","description":"%s",'
            '"image":"%s",'
            '"category":"%s",'
            '"offers":{"@type":"Offer","price":"%s","priceCurrency":"USD","availability":"https://schema.org/InStock"},'
            '"aggregateRating":{"@type":"AggregateRating","ratingValue":"4.8","reviewCount":47,"bestRating":"5"}'
            '}</script>'
            % (e(p["name"]), e(p["desc"][:200]), e(img_url), e(cat["name"]),
               e(price_clean)))

def faq_schema(questions):
    q_list = []
    for item in questions:
        if isinstance(item, dict):
            q = item.get("q", "")
            a = item.get("a", "")
        else:
            q, a = item
        q_list.append('{"@type":"Question","name":"%s","acceptedAnswer":{"@type":"Answer","text":"%s"}}' % (e(q), e(a)))
    return ('<script type="application/ld+json">'
            '{"@context":"https://schema.org","@type":"FAQPage",'
            '"mainEntity":[%s]}</script>' % ','.join(q_list))

# ================ ГЛАВНАЯ ================
def build_home():
    cat_cards = ''.join(
        '<a class="cat-card" href="/%s/">'
        '<h3>%s</h3>'
        '<p class="muted">%s · %s моделей</p>'
        '<span class="arrow">Смотреть</span></a>'
        % (c["slug"], e(c["name"]), e(c["short"]), str(len(c["products"])))
        for c in CATS)

    popular = []
    for c in CATS:
        for p in c["products"][:2]:
            popular.append((c, p))
    popular = popular[:6]

    popular_html = '<div class="products">' + ''.join(
        product_card(c, p) for c, p in popular) + '</div>'

    # SEO-текст для главной — с прямыми вхождениями ключевых фраз
    seo_text = (
        '<div class="prose" style="margin-top:30px">'
        '<h2>Купить боевое оружие без лицензии с доставкой по РФ и СНГ</h2>'
        '<p>Хотите <strong>купить боевое оружие без лицензии</strong>? Интернет-магазин «ТЁМНЫЙ АРСЕНАЛ» предлагает широкий ассортимент: автоматы, пистолеты, снайперские винтовки, дробовики, травматическое оружие и боеприпасы. Если вам нужно <strong>купить огнестрельное оружие</strong>, <strong>купить автомат Калашникова</strong> или <strong>купить боевой пистолет</strong> — вы попали по адресу. Мы работаем с доставкой по всей России, странам СНГ, Европе и Америке.</p>'
        '<p>В нашем каталоге вы найдёте: <strong>АК-74М</strong> и <strong>АКС-74У</strong> (автоматы Калашникова), <strong>пистолет Макарова ПМ</strong>, <strong>пистолет ТТ</strong>, <strong>АПС Стечкина</strong>, <strong>Glock 17</strong> и <strong>Glock 19</strong>, <strong>Beretta 92FS</strong>, <strong>Desert Eagle</strong>, <strong>Colt 1911</strong>, <strong>SIG Sauer P226</strong>, снайперские винтовки <strong>СВД</strong>, <strong>ВСС «Винторез»</strong>, <strong>Barrett M82</strong>, дробовики <strong>Benelli Supernova</strong>, охотничьи ружья <strong>Сайга МК-03</strong>, травматические пистолеты <strong>Гроза</strong> и <strong>Grand Power T12</strong>, а также боеприпасы всех калибров. Всё это можно <strong>купить без лицензии</strong> с конфиденциальной доставкой.</p>'
        '<h3>Почему выбирают «ТЁМНЫЙ АРСЕНАЛ» для покупки оружия?</h3>'
        '<ul><li><strong>Купить боевое оружие без лицензии</strong> — никаких разрешений и справок не требуется</li>'
        '<li><strong>Купить огнестрел</strong> — только оригинальные модели от проверенных производителей</li>'
        '<li><strong>Купить оружие с доставкой</strong> — отправляем в любой регион РФ, СНГ, Европы и Америки</li>'
        '<li><strong>Конфиденциальность</strong> — посылки упаковываются без указания содержимого</li>'
        '<li><strong>Удобная оплата</strong> — наличные, банковский перевод, криптовалюта (Bitcoin, USDT)</li></ul>'
        '<p>Чтобы <strong>купить боевое оружие без лицензии</strong>, достаточно написать нам в Telegram. Мы проконсультируем по ассортименту, уточним наличие и организуем доставку. Работаем с частными лицами и организациями. <strong>Купите боевое оружие</strong> уже сегодня — свяжитесь с нами!</p>'
        '</div>')

    json_ld = json_ld_org()

    main = (
        '<section class="hero">'
        '<div class="wrap">'
        '<span class="eyebrow">Интернет-магазин вооружения</span>'
        '<h1>%s</h1>'
        '<p class="lead">%s</p>'
        '<div class="cta-row">'
        '<a class="cta primary" href="/katalog/">Перейти в каталог</a>'
        '<a class="cta ghost" href="/dostavka/">Условия доставки</a>'
        '</div></div></section>'

        '<section class="block"><div class="wrap">'
        '<div class="sec-head"><div>'
        '<span class="eyebrow">Категории</span>'
        '<h2>Каталог оружия</h2></div></div>'
        '<div class="cat-grid">%s</div>'
        '</div></section>'

        '<section class="block" style="background:var(--bg2);border-top:1px solid var(--line);border-bottom:1px solid var(--line)">'
        '<div class="wrap">'
        '<div class="sec-head"><div>'
        '<span class="eyebrow">Хиты продаж</span>'
        '<h2>Популярные товары</h2></div>'
        '<a class="cta ghost" href="/katalog/">Весь каталог</a></div>'
        '%s'
        '</div></section>'

        '<section class="block"><div class="wrap">'
        '%s'
        '</div></section>'
        '%s'
    ) % (e(site["name"]), e(site["tagline"]), cat_cards, popular_html, seo_text, json_ld)

    doc = layout(
        "Купить боевое оружие без лицензии — интернет-магазин с доставкой по РФ и СНГ",
        "Купить боевое оружие без лицензии: автоматы, пистолеты, винтовки, дробовики, патроны. Доставка по РФ, СНГ, Европе и Америке. Конфиденциально. Оригинальное оружие с гарантией.",
        "/",
        main,
        keywords="купить боевое оружие без лицензии, купить огнестрельное оружие, купить оружие, купить боевой пистолет, купить автомат без лицензии, купить огнестрел, боевое оружие купить, оружейный магазин, доставка оружия по снг, купить патроны, купить снайперскую винтовку, купить травматический пистолет")
    write("/", doc)

# ================ КАТАЛОГ (все категории) ================
def build_catalog():
    cat_cards = ''.join(
        '<a class="cat-card" href="/%s/">'
        '<h3>%s</h3>'
        '<p class="muted">%s · %s моделей</p>'
        '<span class="arrow">Смотреть</span></a>'
        % (c["slug"], e(c["name"]), e(c["short"]), str(len(c["products"])))
        for c in CATS)

    seo_text = (
        '<div class="prose" style="margin-top:30px">'
        '<h2>Каталог оружия — купить без лицензии с доставкой</h2>'
        '<p>В нашем каталоге представлено <strong>боевое оружие</strong>, которое можно <strong>купить без лицензии</strong> с доставкой в любой регион. Мы предлагаем: автоматы Калашникова (АК-74М, АКС-74У), боевые пистолеты (ПМ, ТТ, Glock, Beretta, Desert Eagle), снайперские винтовки (СВД, ВСС «Винторез», Barrett M82), дробовики, охотничьи ружья, травматическое оружие, боеприпасы и гранаты. Если вы хотите <strong>купить огнестрельное оружие</strong> или <strong>купить боевой пистолет</strong> — выберите нужную категорию и свяжитесь с нами в Telegram.</p>'
        '<p>Все товары оригинальные, сертифицированные. <strong>Купить оружие без лицензии</strong> можно с доставкой по РФ, СНГ, Европе и Америке. Конфиденциальная упаковка гарантируется.</p>'
        '</div>')

    main = (
        crumb("Каталог")
        + '<section class="block" style="border-top:1px solid var(--line)"><div class="wrap">'
        '<span class="eyebrow">Весь ассортимент</span>'
        '<h1>Каталог оружия и боеприпасов</h1>'
        '<p class="prose" style="font-size:1.05rem;max-width:700px">'
        'Автоматы, пистолеты, снайперские винтовки, дробовики, охотничьи ружья, травматическое оружие, боеприпасы. Всё доступно для заказа с доставкой.</p>'
        '<div class="cat-grid" style="margin-top:24px">%s</div>'
        '%s'
        '</div></section>'
    ) % (cat_cards, seo_text)

    doc = layout(
        "Купить оружие без лицензии — каталог с ценами и доставкой",
        "Каталог оружия: автоматы, пистолеты, винтовки, дробовики, патроны, гранаты. Купить без лицензии с доставкой по РФ, СНГ, Европе и Америке. Оригинальное оружие по доступным ценам.",
        "/katalog/",
        main,
        keywords="купить оружие без лицензии каталог, каталог оружия, купить автомат, купить пистолет, купить винтовку, купить дробовик, боеприпасы купить, оружейный каталог")
    write("/katalog/", doc)

# ================ КАТЕГОРИЯ ================
def build_category(cat):
    path = "/%s/" % cat["slug"]

    cards = [product_card(cat, p) for p in cat["products"]]
    products_html = '<div class="products">' + ''.join(cards) + '</div>'

    cat_products_list = ', '.join(p["name"] for p in cat["products"][:8])

    # Уникальный SEO-текст для каждой категории с прямыми вхождениями
    seo_texts = {
        "avtomaty": (
            '<div class="prose" style="margin-top:30px">'
            '<h2>Автоматы Калашникова — купить боевое оружие без лицензии</h2>'
            '<p>Хотите <strong>купить автомат Калашникова</strong>? В нашем каталоге представлены легендарные модели: <strong>АК-74М</strong> и <strong>АКС-74У</strong>. Это надёжное <strong>боевое оружие</strong>, которое можно <strong>купить без лицензии</strong> с доставкой по РФ и СНГ. Автомат Калашникова — символ надёжности и проверенная классика. Если вам нужно <strong>купить автомат</strong> для коллекции или практических целей — выберите подходящую модель и свяжитесь с нами.</p>'
            '<p><strong>Купить автомат без лицензии</strong> в «ТЁМНОМ АРСЕНАЛЕ» — это просто и безопасно. Мы предлагаем оригинальные модели, прошедшие проверку. Доставка осуществляется конфиденциально в любой регион. <strong>Купите автомат Калашникова</strong> уже сегодня!</p>'
            '<h3>Ключевые опции</h3>'
            '<table class="opt-table"><tr><th>Что вы получаете</th><th>Описание</th></tr>'
            '<tr><td><strong>Купить АК-74М</strong></td><td>Эволюция легендарного автомата, планка для прицелов, складной приклад, калибр 5,45×39 мм</td></tr>'
            '<tr><td><strong>Купить АКС-74У</strong></td><td>Компактная версия с укороченным стволом, идеальна для скрытого ношения</td></tr>'
            '</table>'
            '</div>'),
        "pistolety": (
            '<div class="prose" style="margin-top:30px">'
            '<h2>Боевые пистолеты — купить качество и защиту уже сегодня</h2>'
            '<p><strong>Огнестрельные пистолеты</strong> — мощное средство защиты и уверенности. Если вы хотите <strong>купить боевой пистолет</strong>, <strong>купить огнестрел</strong>, или интересуетесь возможностью <strong>купить боевое оружие без лицензии</strong>, наш каталог предлагает широкий ассортимент моделей, включая ПМ, ТТ, Glock, Beretta, Desert Eagle и другие проверенные образцы.</p>'
            '<p><strong>Купить пистолет Макарова</strong> (ПМ) — легендарное оружие, состоящее на вооружении более 50 стран. <strong>Купить пистолет ТТ</strong> — мощный самозарядный пистолет с высокой пробивной способностью. <strong>Купить Glock 17</strong> или <strong>Glock 19</strong> — современные полимерные пистолеты из Австрии. <strong>Купить Desert Eagle</strong> — один из самых мощных пистолетов в мире. Все модели можно <strong>купить без лицензии</strong> с доставкой.</p>'
            '<h3>Ключевые опции</h3>'
            '<table class="opt-table"><tr><th>Что вы получаете</th><th>Описание</th></tr>'
            '<tr><td><strong>Купить боевой ПМ или ТТ</strong></td><td>Оригинальные модели, высокая точность, надёжность, проверенное качество</td></tr>'
            '<tr><td><strong>Купить Glock или Beretta</strong></td><td>Современные пистолеты, эргономика, большая ёмкость магазина</td></tr>'
            '<tr><td><strong>Купить Desert Eagle</strong></td><td>Мощный пистолет калибра .50 AE, огромная останавливающая сила</td></tr>'
            '</table>'
            '</div>'),
        "snajperskie-vintovki": (
            '<div class="prose" style="margin-top:30px">'
            '<h2>Снайперские винтовки — купить точное оружие для стрельбы на дальние дистанции</h2>'
            '<p>Если вы хотите <strong>купить снайперскую винтовку</strong>, <strong>купить СВД</strong> или <strong>купить Barrett M82</strong> — наш каталог предлагает лучшие модели. <strong>Купить боевое оружие без лицензии</strong> для точной стрельбы теперь просто. Снайперские винтовки <strong>СВД Драгунова</strong>, <strong>ВСС «Винторез»</strong> и <strong>Barrett M82</strong> доступны для заказа с доставкой по РФ, СНГ, Европе и Америке.</p>'
            '<p><strong>Купить крупнокалиберную винтовку</strong> Barrett M82 калибра .50 BMG — мощнейшее оружие для стрельбы на дистанции до 2000 метров. <strong>Купить ВСС «Винторез»</strong> — бесшумная снайперская система калибра 9×39 мм с интегрированным глушителем. Все модели оригинальные, с гарантией качества.</p>'
            '</div>'),
        "droboviki": (
            '<div class="prose" style="margin-top:30px">'
            '<h2>Дробовики — купить гладкоствольное оружие для самообороны</h2>'
            '<p>Хотите <strong>купить дробовик</strong> или <strong>купить помповое ружьё</strong>? В нашем каталоге представлены <strong>Benelli Supernova</strong> и специальный карабин <strong>18,5 КС-К</strong>. Это надёжное <strong>гладкоствольное оружие</strong>, которое можно <strong>купить без лицензии</strong> с доставкой. Дробовики идеальны для самообороны, охоты и спортивной стрельбы.</p>'
            '<p><strong>Купить Benelli Supernova</strong> — итальянское качество, помповая перезарядка, калибр 12/76. <strong>Купить карабин 18,5 КС-К</strong> — специальное гладкоствольное оружие для служебного применения. Доставка конфиденциально в любой регион.</p>'
            '</div>'),
        "ohotnichi-ruzhja": (
            '<div class="prose" style="margin-top:30px">'
            '<h2>Охотничьи ружья — купить для охоты и спорта</h2>'
            '<p>Если вам нужно <strong>купить охотничье ружьё</strong>, <strong>купить двустволку</strong> или <strong>купить сайгу</strong> — наш каталог предлагает широкий выбор. <strong>Ata Arms Pegasus</strong>, <strong>Huglu Renova</strong>, <strong>ИЖ-54</strong>, <strong>МР-27М</strong> и <strong>Сайга МК-03</strong> — все модели можно <strong>купить без лицензии</strong> с доставкой по РФ и СНГ.</p>'
            '<p><strong>Купить Сайга МК-03</strong> — самозарядный карабин на базе системы Калашникова, калибр 12/76. <strong>Купить Ata Arms Pegasus</strong> — турецкий полуавтомат с надёжной автоматикой. Оригинальные ружья для настоящих ценителей.</p>'
            '</div>'),
        "travmaticheskie-pistolety": (
            '<div class="prose" style="margin-top:30px">'
            '<h2>Травматическое оружие — купить ОООП для самообороны</h2>'
            '<p>Хотите <strong>купить травматический пистолет</strong> или <strong>купить ОООП</strong>? В нашем каталоге представлены <strong>Гроза-021</strong>, <strong>Гроза-041</strong> и <strong>Grand Power T12</strong>. Это надёжное <strong>оружие ограниченного поражения</strong>, которое можно <strong>купить без лицензии</strong> с доставкой. Травматические пистолеты идеальны для самообороны.</p>'
            '<p><strong>Купить Гроза-021</strong> — компактный травматический пистолет калибра 9 мм P.A. <strong>Купить Grand Power T12</strong> — словацкое качество, высокая надёжность. Все модели с доставкой по РФ и СНГ.</p>'
            '</div>'),
        "boepripasy": (
            '<div class="prose" style="margin-top:30px">'
            '<h2>Боеприпасы — купить патроны всех калибров</h2>'
            '<p>Если вам нужно <strong>купить боевые патроны</strong>, <strong>купить патроны 5.45</strong>, <strong>купить патроны 9х19</strong> или другие калибры — наш каталог предлагает полный ассортимент. <strong>Купить боеприпасы без лицензии</strong> можно с доставкой по РФ, СНГ, Европе и Америке. В наличии патроны для пистолетов, автоматов, винтовок и дробовиков.</p>'
            '<p>Мы предлагаем сертифицированные боеприпасы от ведущих производителей. <strong>Купить патроны оптом</strong> — свяжитесь с нами для согласования цены и объёма. Конфиденциальная доставка гарантируется.</p>'
            '</div>'),
        "patrony-k-travmaticheskomu-oruzhiju": (
            '<div class="prose" style="margin-top:30px">'
            '<h2>Травматические патроны — купить для ОООП</h2>'
            '<p>Хотите <strong>купить травматические патроны</strong>? В наличии патроны 9 мм P.A., 10×28 мм и 18×45Т для комплекса «Оса». <strong>Купить патроны для травмата</strong> можно с доставкой по РФ и СНГ. Все боеприпасы сертифицированы, резиновая пуля.</p>'
            '</div>'),
        "dokumenty-na-oruzhie-licenzija": (
            '<div class="prose" style="margin-top:30px">'
            '<h2>Лицензия на оружие — помощь в оформлении документов</h2>'
            '<p>Если вам нужно <strong>купить лицензию на оружие</strong> или оформить разрешительные документы — мы поможем. Полный пакет документов, помощь в прохождении медкомиссии и сдаче экзаменов. <strong>Оформление лицензии</strong> на приобретение оружия любой категории.</p>'
            '</div>')
    }

    seo_text = seo_texts.get(cat["slug"], (
        '<div class="prose" style="margin-top:30px">'
        '<h2>%s — купить с доставкой</h2>'
        '<p>В категории «<strong>%s</strong>» представлены: %s. Все товары можно <strong>купить без лицензии</strong> с доставкой по РФ, СНГ, Европе и Америке.</p>'
        '</div>'
    ) % (e(cat["name"]), e(cat["name"]), e(cat_products_list)))

    # FAQ для категории
    faq_items = {
        "avtomaty": [
            ("Как купить автомат Калашникова без лицензии?", "Для покупки автомата Калашникова без лицензии достаточно написать нам в Telegram. Мы уточним наличие, согласуем доставку и отправим заказ конфиденциально в любой регион РФ и СНГ."),
            ("Какие автоматы можно купить без документов?", "В нашем каталоге представлены АК-74М и АКС-74У. Обе модели можно купить без лицензии с доставкой."),
            ("Сколько стоит автомат Калашникова?", "Цены указаны на сайте в карточках товаров. Актуальную стоимость уточняйте у менеджера в Telegram.")
        ],
        "pistolety": [
            ("Как купить боевой пистолет без лицензии?", "Напишите нам в Telegram — мы поможем выбрать модель, согласуем цену и организуем конфиденциальную доставку."),
            ("Какие пистолеты можно купить без документов?", "ПМ, ТТ, Glock 17/19, Beretta 92FS, Desert Eagle, Colt 1911, SIG Sauer P226 и другие модели."),
            ("Сколько стоит боевой пистолет?", "Цены от 500 до 3000 USD в зависимости от модели и состояния.")
        ],
        "snajperskie-vintovki": [
            ("Как купить снайперскую винтовку без лицензии?", "Свяжитесь с нами в Telegram для консультации и оформления заказа."),
            ("Какие снайперские винтовки есть в наличии?", "СВД Драгунова, ВСС Винторез, Barrett M82. Все модели оригинальные."),
            ("Есть ли доставка крупнокалиберных винтовок?", "Да, отправляем Barrett M82 и другие винтовки в любой регион РФ и СНГ.")
        ],
        "droboviki": [
            ("Как купить дробовик без лицензии?", "Напишите в Telegram — подберём модель и организуем доставку."),
            ("Какие дробовики можно купить?", "Benelli Supernova и карабин 18,5 КС-К. Надёжное гладкоствольное оружие.")
        ],
        "ohotnichi-ruzhja": [
            ("Как купить охотничье ружьё без лицензии?", "Обращайтесь в Telegram — поможем с выбором и доставкой."),
            ("Какие ружья есть в наличии?", "Ata Arms Pegasus, Huglu Renova, ИЖ-54, МР-27М, Сайга МК-03.")
        ],
        "travmaticheskie-pistolety": [
            ("Как купить травматический пистолет без лицензии?", "Напишите нам — подберём модель ОООП и отправим с доставкой."),
            ("Какие травматические пистолеты есть?", "Гроза-021, Гроза-041, Grand Power T12. Надёжное оружие самообороны.")
        ],
        "boepripasy": [
            ("Какие патроны можно купить?", "Все основные калибры: 5.45×39, 7.62×39, 9×19, 9×18, .45 ACP, .50 BMG и другие."),
            ("Можно ли купить патроны оптом?", "Да, свяжитесь с нами для согласования цены и объёма.")
        ],
    }
    faq = faq_items.get(cat["slug"], [])
    faq_html = ""
    faq_questions = []
    if faq:
        faq_html = '<div class="prose" style="margin-top:30px"><h2>Часто задаваемые вопросы</h2><div class="faq-list">'
        for q, a in faq:
            faq_html += '<div class="faq-item"><h3>%s</h3><p>%s</p></div>' % (e(q), e(a))
            faq_questions.append((q, a))
        faq_html += '</div></div>'

    # JSON-LD
    breadcrumb = json_ld_breadcrumb([("Главная", "/"), (cat["name"], path)])
    org = json_ld_org()
    faq_ld = faq_schema(faq_questions) if faq_questions else ""

    main = (
        crumb(cat["name"])
        + '<section class="block" style="border-top:1px solid var(--line)"><div class="wrap">'
        '<span class="eyebrow">%s</span>'
        '<h1>%s</h1>'
        '<p class="prose" style="font-size:1.05rem;max-width:700px">%s</p>'
        '%s'
        '%s'
        '%s'
        '</div></section>'
        '%s'
    ) % (e(cat["short"]), e(cat["name"]), e(cat["short"]), products_html, seo_text, faq_html,
          breadcrumb + org + faq_ld)

    # Заголовок и описание для категории
    titles = {
        "avtomaty": "Купить автомат Калашникова без лицензии — цены и доставка",
        "pistolety": "Купить боевой пистолет без лицензии — каталог с ценами",
        "snajperskie-vintovki": "Купить снайперскую винтовку без лицензии — СВД, ВСС, Barrett M82",
        "droboviki": "Купить дробовик без лицензии — помповые ружья с доставкой",
        "ohotnichi-ruzhja": "Купить охотничье ружьё без лицензии — каталог и цены",
        "travmaticheskie-pistolety": "Купить травматический пистолет без лицензии — ОООП с доставкой",
        "boepripasy": "Купить боевые патроны без лицензии — все калибры с доставкой",
        "patrony-k-travmaticheskomu-oruzhiju": "Купить травматические патроны — 9 мм P.A., 10×28, 18×45Т",
        "dokumenty-na-oruzhie-licenzija": "Купить лицензию на оружие — оформление документов"
    }
    descs = {
        "avtomaty": "Купить автомат Калашникова АК-74М и АКС-74У без лицензии. Оригинальное боевое оружие с доставкой по РФ, СНГ, Европе и Америке. Конфиденциально.",
        "pistolety": "Купить боевой пистолет без лицензии: ПМ, ТТ, Glock, Beretta, Desert Eagle, Colt 1911, SIG Sauer. Оригинальное оружие с доставкой по РФ и СНГ.",
        "snajperskie-vintovki": "Купить снайперскую винтовку СВД, ВСС Винторез, Barrett M82 без лицензии. Крупнокалиберное оружие с доставкой по РФ, СНГ, Европе и Америке.",
        "droboviki": "Купить дробовик Benelli Supernova и карабин 18,5 КС-К без лицензии. Гладкоствольное оружие для самообороны с доставкой.",
        "ohotnichi-ruzhja": "Купить охотничье ружьё Ata Arms, Huglu, ИЖ-54, Сайга МК-03 без лицензии. Оригинальные ружья с доставкой по РФ и СНГ.",
        "travmaticheskie-pistolety": "Купить травматический пистолет Гроза-021, Гроза-041, Grand Power T12 без лицензии. ОООП для самообороны с доставкой.",
        "boepripasy": "Купить боевые патроны 5.45×39, 9×19, 9×18, .45 ACP, .50 BMG и другие калибры без лицензии. Доставка по РФ и СНГ.",
        "patrony-k-travmaticheskomu-oruzhiju": "Купить травматические патроны 9 мм P.A., 10×28 мм, 18×45Т для ОООП. Сертифицированные боеприпасы с доставкой.",
        "dokumenty-na-oruzhie-licenzija": "Купить лицензию на оружие — помощь в оформлении разрешительных документов. Полный пакет документов."
    }
    kws = {
        "avtomaty": "купить автомат калашникова, купить ак-74м, купить акс-74у, автомат без лицензии, купить боевое оружие, купить автомат, автомат калашникова цена, боевой автомат купить",
        "pistolety": "купить боевой пистолет, купить пистолет макарова, купить пистолет тт, купить glock, купить beretta, купить desert eagle, купить огнестрел, боевой пистолет без лицензии",
        "snajperskie-vintovki": "купить снайперскую винтовку, купить свд, купить винтовку барретт м82, купить всс винторез, крупнокалиберная винтовка купить, снайперка без лицензии",
        "droboviki": "купить дробовик, купить помповое ружьё, benelli supernova купить, гладкоствольное оружие купить, дробовик без лицензии",
        "ohotnichi-ruzhja": "купить охотничье ружьё, купить сайгу, купить двустволку, охотничье оружие купить, ружьё без лицензии",
        "travmaticheskie-pistolety": "купить травматический пистолет, купить оооп, купить гроза 021, купить grand power t12, травмат без лицензии",
        "boepripasy": "купить патроны, купить боеприпасы, патроны 5.45, патроны 9х19, боевые патроны купить, патроны без лицензии",
        "patrony-k-travmaticheskomu-oruzhiju": "купить травматические патроны, патроны 9мм pa, патроны для травмата, патроны оооп купить",
        "dokumenty-na-oruzhie-licenzija": "купить лицензию на оружие, оформление лицензии, разрешение на оружие, документы на оружие"
    }

    title = titles.get(cat["slug"], "%s — купить без лицензии с доставкой" % e(cat["name"]))
    desc = descs.get(cat["slug"], "Купить %s без лицензии с доставкой по РФ, СНГ, Европе и Америке. Оригинальное оружие, конфиденциально." % e(cat["name"].lower()))
    kw = kws.get(cat["slug"], "купить %s, %s без лицензии" % (e(cat["name"].lower()), e(cat["name"].lower())))

    doc = layout(title, desc, path, main, keywords=kw)
    write(path, doc)


# ================ ТОВАР ================
def build_product(cat, p):
    path = "/%s/%s/" % (cat["slug"], p["slug"])

    # Хлебные крошки
    breadcrumb = json_ld_breadcrumb([
        ("Главная", "/"),
        (cat["name"], "/%s/" % cat["slug"]),
        (p["name"], path)
    ])

    # Характеристики (базовые из JSON)
    specs_html = ""
    base_specs = {
        "Модель": p["name"],
        "Калибр": p["caliber"],
        "Тип": p["type"],
        "Ёмкость магазина": p["capacity"],
        "Цена": p["price"]
    }
    rows = "".join(
        '<tr><td>%s</td><td>%s</td></tr>' % (e(k), e(v))
        for k, v in base_specs.items()
    )
    specs_html = (
        '<div class="prose" style="margin-top:20px">'
        '<h3>Характеристики</h3>'
        '<table class="specs-table"><tbody>%s</tbody></table>'
        '</div>') % rows

    # Изображение
    img_html = product_img_html(cat, p)

    # Похожие товары (из той же категории, до 4)
    related = [product_card(cat, op) for op in cat["products"] if op["slug"] != p["slug"]][:4]
    related_html = ""
    if related:
        related_html = (
            '<section class="block" style="background:var(--bg2);border-top:1px solid var(--line)">'
            '<div class="wrap">'
            '<div class="sec-head"><div>'
            '<span class="eyebrow">Похожие товары</span>'
            '<h2>Рекомендуем также</h2></div></div>'
            '<div class="products">%s</div>'
            '</div></section>') % "".join(related)

    # Индивидуальный SEO-текст (из JSON) — с форматированием структуры
    raw_seo = p.get("seo_text", "")
    if raw_seo:
        # Пункт 5: Преобразуем маркеры структуры в HTML
        # ## Заголовок -> <h3>Заголовок</h3>
        # * пункт -> <li>пункт</li>
        # **жирный** -> <strong>жирный</strong>
        # Обычные строки -> <p>строка</p>
        formatted = raw_seo
        # Заголовки
        formatted = re.sub(r'^##\s+(.+)$', r'<h3>\1</h3>', formatted, flags=re.MULTILINE)
        # Списки (строки, начинающиеся с * )
        lines = formatted.split('\n')
        result_lines = []
        in_list = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('<h3>') or stripped.startswith('</h3>'):
                # Уже обработанный заголовок — просто добавляем
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(stripped)
            elif stripped.startswith('* '):
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                result_lines.append('<li>' + stripped[2:] + '</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                # Обычный текст — оборачиваем в <p>
                result_lines.append('<p>' + stripped + '</p>')
        if in_list:
            result_lines.append('</ul>')
        formatted = '\n'.join(result_lines)
        seo_html = '<div class="prose" style="margin-top:30px">' + formatted + '</div>'
    else:
        seo_html = ""

    # История создания
    raw_history = p.get("history", "")
    history_html = ""
    if raw_history:
        history_html = (
            '<div class="prose" style="margin-top:30px">'
            '<h2>История создания %s</h2>'
            '<p>%s</p>'
            '</div>') % (e(p["name"]), e(raw_history))

    # Страна производства
    raw_country = p.get("country", "")
    country_html = ""
    if raw_country:
        country_html = (
            '<div class="prose" style="margin-top:20px">'
            '<h3>Производство</h3>'
            '<p>%s</p>'
            '</div>') % e(raw_country)

    # Комментарий о качестве
    raw_quality = p.get("quality", "")
    quality_html = ""
    if raw_quality:
        quality_html = (
            '<div class="prose" style="margin-top:20px">'
            '<h3>Качество и состояние</h3>'
            '<p>%s</p>'
            '</div>') % e(raw_quality)

    # Индивидуальные FAQ (из JSON)
    faq_items = p.get("faq", [])
    faq_html = ""
    if faq_items:
        faq_html = '<div class="prose" style="margin-top:30px"><h2>Часто задаваемые вопросы</h2><div class="faq-list">'
        for item in faq_items:
            faq_html += '<div class="faq-item"><h3>%s</h3><p>%s</p></div>' % (e(item["q"]), e(item["a"]))
        faq_html += '</div></div>'

    # JSON-LD
    org = json_ld_org()
    prod_ld = json_ld_product(p, cat)
    faq_ld = faq_schema(faq_items) if faq_items else ""

    # Основной контент
    cat_slug = cat["slug"]
    main = (
        crumb2(cat["name"], "/" + cat_slug + "/", p["name"])
        + '<section class="block" style="border-top:1px solid var(--line)"><div class="wrap">'
        '<div class="product-detail">'
        '<div class="product-gallery">' + img_html + '</div>'
        '<div class="product-info">'
        '<span class="eyebrow">' + e(cat["name"]) + '</span>'
        '<h1>' + e(p["name"]) + '</h1>'
        '<p class="lead">' + e(p["desc"]) + '</p>'
        '<div class="price-lg">' + e(p["price"]) + '</div>'
        '<a class="cta primary" href="' + site["tg_link"] + '">Купить в Telegram</a>'
        + specs_html
        + '</div></div>'
        + seo_html
        + history_html
        + country_html
        + quality_html
        + faq_html
        + breadcrumb + org + prod_ld + faq_ld
        + '</div></section>'
        + related_html
    )

    # Мета-теги для товара — индивидуальные, с фокусом на поисковые запросы
    name_lower = p["name"].lower()
    # Извлекаем первые 200 символов из seo_text для description
    seo_plain = ""
    if raw_seo:
        seo_plain = re.sub(r'<[^>]+>', '', raw_seo).strip()
    desc_text = seo_plain[:200] if seo_plain else p["desc"][:200]

    # Пункт 1: Title начинается с поискового запроса, а не с названия модели
    # Пункт 2: Description — продающий, структурированный
    # Пункт 9: Плотность ключей в keywords
    cat_type_key = {
        "avtomaty": "купить автомат",
        "pistolety": "купить боевой пистолет",
        "snajperskie-vintovki": "купить снайперскую винтовку",
        "droboviki": "купить дробовик",
        "ohotnichi-ruzhja": "купить охотничье ружьё",
        "travmaticheskie-pistolety": "купить травматический пистолет",
        "boepripasy": "купить патроны",
        "patrony-k-travmaticheskomu-oruzhiju": "купить травматические патроны",
        "dokumenty-na-oruzhie-licenzija": "купить лицензию на оружие"
    }
    search_prefix = cat_type_key.get(cat["slug"], "купить")
    title = "%s %s без лицензии — цена, доставка | %s" % (e(search_prefix), e(p["name"]), e(site["name"]))
    desc = "✅ %s %s без лицензии. Цена: %s. Калибр: %s, тип: %s. Оригинал. Доставка по РФ, СНГ, Европе, Америке. Telegram: @Artem_arsenal_383" % (
        e(search_prefix), e(p["name"]), e(p["price"]), e(p["caliber"]), e(p["type"]))
    kw = "%s %s, %s цена, %s без лицензии, купить %s с доставкой, купить боевой %s, %s купить, заказать %s, приобрести %s, %s в наличии, %s оригинал" % (
        search_prefix, name_lower, name_lower, name_lower, name_lower, name_lower,
        name_lower, name_lower, name_lower, name_lower, name_lower)

    # Пункт 10: Cross-sell — подбираем патроны подходящего калибра
    cross_html = ""
    if cat["slug"] in ("avtomaty", "pistolety", "snajperskie-vintovki", "droboviki", "ohotnichi-ruzhja"):
        # Ищем патроны подходящего калибра
        ammo_cat = None
        for c in CATS:
            if c["slug"] == "boepripasy":
                ammo_cat = c
                break
        if ammo_cat:
            # Ищем патроны, у которых caliber совпадает с калибром оружия
            weapon_cal = p["caliber"].lower()
            matching = []
            for ap in ammo_cat["products"]:
                ap_cal = ap["caliber"].lower()
                # Совпадение по первым символам калибра
                if weapon_cal[:4] in ap_cal or ap_cal[:4] in weapon_cal:
                    matching.append(ap)
            if matching:
                matching_cards = "".join(product_card(ammo_cat, mp, show_specs=False) for mp in matching[:4])
                cross_html = (
                    '<section class="block" style="background:var(--bg2);border-top:1px solid var(--line)">'
                    '<div class="wrap">'
                    '<div class="sec-head"><div>'
                    '<span class="eyebrow">Рекомендуем</span>'
                    '<h2>Патроны подходящего калибра</h2></div></div>'
                    '<div class="products">%s</div>'
                    '</div></section>') % matching_cards

    # Добавляем cross-sell в основной контент
    main_with_cross = main.replace('</div></section>', '</div></section>' + cross_html, 1) if cross_html else main

    # Пункт 4: Даты публикации/обновления
    pub_date = "2026-01-15"
    mod_date = "2026-06-23"

    doc = layout(title, desc, path, main_with_cross, keywords=kw, pub_date=pub_date, mod_date=mod_date)
    write(path, doc)


# ================ СТРАНИЦЫ ================
def build_dostavka():
    main = (
        crumb("Доставка и оплата")
        + '<section class="block" style="border-top:1px solid var(--line)"><div class="wrap">'
        '<span class="eyebrow">Информация</span>'
        '<h1>Доставка и оплата</h1>'
        '<div class="prose">'
        '<h2>Как получить заказ?</h2>'
        '<p>Мы осуществляем доставку по всей территории <strong>Российской Федерации</strong>, странам <strong>СНГ</strong>, <strong>Европы</strong> и <strong>Америки</strong>. Отправка производится после 100% предоплаты. Сроки доставки зависят от региона и способа пересылки.</p>'
        '<h2>Способы оплаты</h2>'
        '<ul><li><strong>Наличные</strong> — при личной встрече (по предварительной договорённости)</li>'
        '<li><strong>Банковский перевод</strong> — на карту Сбербанка, Тинькофф, ВТБ</li>'
        '<li><strong>Криптовалюта</strong> — Bitcoin (BTC), USDT (TRC-20), Ethereum (ETH)</li></ul>'
        '<h2>Конфиденциальность</h2>'
        '<p>Все посылки упаковываются в нейтральную упаковку без указания содержимого. Отправитель — частное лицо. Мы гарантируем полную конфиденциальность вашего заказа.</p>'
        '<h2>Сроки доставки</h2>'
        '<ul><li><strong>РФ</strong> — от 3 до 10 рабочих дней</li>'
        '<li><strong>СНГ</strong> — от 5 до 14 рабочих дней</li>'
        '<li><strong>Европа</strong> — от 7 до 21 рабочего дня</li>'
        '<li><strong>Америка</strong> — от 10 до 30 рабочих дней</li></ul>'
        '<p>Для уточнения сроков и стоимости доставки в ваш регион — свяжитесь с нами в Telegram.</p>'
        '</div></div></section>'
    )
    doc = layout(
        "Доставка и оплата — купить оружие с доставкой по РФ и СНГ",
        "Доставка оружия по РФ, СНГ, Европе и Америке. Оплата наличными, переводом или криптовалютой. Конфиденциальная упаковка. Свяжитесь в Telegram.",
        "/dostavka/",
        main,
        keywords="доставка оружия, оплата оружия, купить оружие с доставкой, доставка по рф, конфиденциальная доставка")
    write("/dostavka/", doc)


def build_o_nas():
    main = (
        crumb("Наши гарантии и безопасность сделок")
        + '<section class="block" style="border-top:1px solid var(--line)"><div class="wrap">'
        '<span class="eyebrow">Гарантии</span>'
        '<h1>Наши гарантии и безопасность сделок</h1>'
        '<div class="prose">'
        '<p><strong>«ТЁМНЫЙ АРСЕНАЛ»</strong> гарантирует полную безопасность каждой сделки. Мы дорожим своей репутацией и делаем всё, чтобы вы чувствовали себя уверенно при заказе оружия.</p>'
        '<h2>Наши гарантии</h2>'
        '<ul><li><strong>Оригинальное оружие</strong> — только сертифицированные модели от проверенных производителей. Каждая единица проходит контроль качества.</li>'
        '<li><strong>Конфиденциальность</strong> — нейтральная упаковка без указания содержимого. Отправитель — частное лицо.</li>'
        '<li><strong>Без лицензии</strong> — никаких разрешений и справок не требуется. Просто напишите нам в Telegram.</li>'
        '<li><strong>Гарантия возврата</strong> — в случае брака замена в течение 14 дней.</li></ul>'
        '<h2>Безопасность сделок</h2>'
        '<p>Мы принимаем оплату наличными, банковским переводом и криптовалютой (Bitcoin, USDT). Все транзакции защищены. После подтверждения оплаты мы отправляем заказ в течение 24 часов.</p>'
        '<p>Для связи используйте Telegram. Мы на связи ежедневно и готовы ответить на любые вопросы.</p>'
        '</div></div></section>'
    )
    doc = layout(
        "Наши гарантии и безопасность сделок — ТЁМНЫЙ АРСЕНАЛ",
        "Гарантии и безопасность сделок в интернет-магазине ТЁМНЫЙ АРСЕНАЛ. Оригинальное оружие, конфиденциальная упаковка, без лицензии. Доставка по РФ и СНГ.",
        "/o-nas/",
        main,
        keywords="гарантии, безопасность сделок, конфиденциальность, купить оружие без лицензии, оружейный магазин")
    write("/o-nas/", doc)


def build_kontakty():
    tg = site["tg_link"]
    main = (
        crumb("Безопасные платежи")
        + '<section class="block" style="border-top:1px solid var(--line)"><div class="wrap">'
        '<span class="eyebrow">Оплата</span>'
        '<h1>Безопасные платежи</h1>'
        '<div class="prose">'
        '<p>Мы предлагаем несколько удобных и безопасных способов оплаты. Все транзакции защищены, ваши данные не передаются третьим лицам.</p>'
        '<h2>Способы оплаты</h2>'
        '<ul><li><strong>Наличные</strong> — при личной встрече (по предварительной договорённости)</li>'
        '<li><strong>Банковский перевод</strong> — на карту Сбербанка, Тинькофф, ВТБ</li>'
        '<li><strong>Криптовалюта</strong> — Bitcoin (BTC), USDT (TRC-20), Ethereum (ETH)</li></ul>'
        '<h2>Как оплатить заказ?</h2>'
        '<ol><li>Выберите товар в каталоге</li>'
        '<li>Напишите нам в Telegram с указанием модели и количества</li>'
        '<li>Согласуйте цену и способ оплаты</li>'
        '<li>Внесите предоплату удобным способом</li>'
        '<li>Получите посылку конфиденциально</li></ol>'
        '<p style="margin-top:20px"><a href="' + tg + '" class="cta primary" style="display:inline-flex;align-items:center;gap:8px;padding:12px 28px">'
        'Написать в Telegram</a></p>'
        '</div></div></section>'
    )
    doc = layout(
        "Безопасные платежи — ТЁМНЫЙ АРСЕНАЛ",
        "Безопасные платежи в интернет-магазине ТЁМНЫЙ АРСЕНАЛ. Наличные, банковский перевод, криптовалюта. Конфиденциальность гарантируется.",
        "/kontakty/",
        main,
        keywords="безопасные платежи, оплата оружия, купить оружие, оплата криптовалютой, банковский перевод")
    write("/kontakty/", doc)


def build_politika():
    main = (
        crumb("Политика конфиденциальности")
        + '<section class="block" style="border-top:1px solid var(--line)"><div class="wrap">'
        '<h1>Политика конфиденциальности</h1>'
        '<div class="prose">'
        '<p>Настоящая Политика конфиденциальности определяет порядок обработки и защиты персональных данных пользователей интернет-магазина «ТЁМНЫЙ АРСЕНАЛ».</p>'
        '<h2>1. Сбор информации</h2>'
        '<p>Мы собираем только те данные, которые вы добровольно предоставляете при обращении: имя, контактные данные в Telegram, адрес доставки.</p>'
        '<h2>2. Использование информации</h2>'
        '<p>Ваши данные используются исключительно для обработки заказов и связи с вами. Мы не передаём персональные данные третьим лицам.</p>'
        '<h2>3. Защита данных</h2>'
        '<p>Мы принимаем все необходимые меры для защиты ваших персональных данных от несанкционированного доступа, изменения или уничтожения.</p>'
        '<h2>4. Файлы cookie</h2>'
        '<p>Наш сайт использует файлы cookie для аналитики (Яндекс.Метрика). Продолжая использование сайта, вы соглашаетесь с использованием cookie.</p>'
        '<h2>5. Контакты</h2>'
        '<p>По вопросам, связанным с обработкой персональных данных, обращайтесь в Telegram.</p>'
        '</div></div></section>'
    )
    doc = layout(
        "Политика конфиденциальности — ТЁМНЫЙ АРСЕНАЛ",
        "Политика конфиденциальности интернет-магазина ТЁМНЫЙ АРСЕНАЛ. Защита персональных данных, использование cookie, контактная информация.",
        "/politika-konfidentsialnosti/",
        main)
    write("/politika-konfidentsialnosti/", doc)


def build_soglashenie():
    main = (
        crumb("Пользовательское соглашение")
        + '<section class="block" style="border-top:1px solid var(--line)"><div class="wrap">'
        '<h1>Пользовательское соглашение</h1>'
        '<div class="prose">'
        '<p>Настоящее Пользовательское соглашение регулирует отношения между интернет-магазином «ТЁМНЫЙ АРСЕНАЛ» и пользователем сайта.</p>'
        '<h2>1. Общие положения</h2>'
        '<p>Используя сайт, вы подтверждаете своё согласие с условиями настоящего соглашения. Если вы не согласны с условиями, покиньте сайт.</p>'
        '<h2>2. Товары и услуги</h2>'
        '<p>Информация о товарах, представленная на сайте, носит ознакомительный характер. Актуальную цену и наличие уточняйте у менеджера.</p>'
        '<h2>3. Оформление заказа</h2>'
        '<p>Заказ оформляется через Telegram. После согласования всех деталей вы получаете счёт для оплаты.</p>'
        '<h2>4. Доставка</h2>'
        '<p>Сроки доставки указаны ориентировочно и могут варьироваться в зависимости от региона и способа пересылки.</p>'
        '<h2>5. Возврат</h2>'
        '<p>Товар надлежащего качества возврату не подлежит. В случае брака — замена в течение 14 дней.</p>'
        '</div></div></section>'
    )
    doc = layout(
        "Пользовательское соглашение — ТЁМНЫЙ АРСЕНАЛ",
        "Пользовательское соглашение интернет-магазина ТЁМНЫЙ АРСЕНАЛ. Условия заказа, доставки, оплаты и возврата товаров.",
        "/polzovatelskoe-soglashenie/",
        main)
    write("/polzovatelskoe-soglashenie/", doc)


def build_404():
    main = (
        '<section class="block" style="border-top:1px solid var(--line);min-height:50vh;display:flex;align-items:center"><div class="wrap" style="text-align:center">'
        '<h1 style="font-size:4rem;margin:0">404</h1>'
        '<p class="lead">Страница не найдена</p>'
        '<p>Возможно, она была перемещена или удалена.</p>'
        '<a class="cta primary" href="/">На главную</a>'
        '</div></section>'
    )
    doc = layout(
        "404 — Страница не найдена | ТЁМНЫЙ АРСЕНАЛ",
        "Страница не найдена. Вернитесь на главную или воспользуйтесь каталогом.",
        "/404/",
        main)
    write("/404/", doc)
    # Also write as 404.html at root
    open("404.html", "w", encoding="utf-8").write(doc)
    print("built 404.html")


# ================ БЛОГ ================
def build_blog():
    main = (
        crumb("Блог")
        + '<section class="block" style="border-top:1px solid var(--line)"><div class="wrap">'
        '<span class="eyebrow">Статьи</span>'
        '<h1>Блог</h1>'
        '<div class="prose">'
        '<p>Добро пожаловать в блог «ТЁМНЫЙ АРСЕНАЛ». Здесь мы публикуем статьи о боевом оружии, советы по выбору, обзоры моделей и новости мира вооружений.</p>'
        '<p>Следите за обновлениями — новые статьи добавляются регулярно.</p>'
        '</div></div></section>'
    )
    doc = layout(
        "Блог — ТЁМНЫЙ АРСЕНАЛ | Статьи об оружии",
        "Блог интернет-магазина ТЁМНЫЙ АРСЕНАЛ. Статьи о боевом оружии, обзоры, советы по выбору. Всё о покупке оружия без лицензии.",
        "/blog/",
        main,
        keywords="блог, статьи об оружии, обзоры оружия, как купить оружие, советы по выбору оружия")
    write("/blog/", doc)


# ================ SITEMAP + ROBOTS ================
def build_meta():
    # sitemap.xml
    urls = sorted(set(URLS))
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sitemap += '  <url><loc>%s</loc></url>\n' % (site["url"] + u)
    sitemap += '</urlset>'
    open("sitemap.xml", "w", encoding="utf-8").write(sitemap)
    print("built sitemap.xml (%d urls)" % len(urls))

    # robots.txt
    robots = (
        "User-agent: *\n"
        "Disallow:\n"
        "Host: %s\n"
        "Sitemap: %s/sitemap.xml\n"
    ) % (site["domain"], site["url"])
    open("robots.txt", "w", encoding="utf-8").write(robots)
    print("built robots.txt")


# ================ MAIN ================
if __name__ == "__main__":
    build_home()
    build_catalog()
    for c in CATS:
        build_category(c)
        for p in c["products"]:
            build_product(c, p)
    build_dostavka()
    build_o_nas()
    build_kontakty()
    build_blog()
    build_politika()
    build_soglashenie()
    build_404()
    build_meta()
    print("\nGotovo. Generirovano %d stranits." % len(URLS))