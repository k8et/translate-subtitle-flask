import sys
import re
import asyncio
from pathlib import Path
import pysrt
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm as async_tqdm
import genanki
import deepl

# Ваш API-ключ DeepL
DEEPL_AUTH_KEY = "fbb22451-a491-4051-838e-8f14ac778fc3:fx"

# Инициализация клиента DeepL
translator = deepl.Translator(DEEPL_AUTH_KEY)


def strip_tags(text):
    return BeautifulSoup(text, "html.parser").get_text()


def ends_sentence(text):
    text = text.strip()
    if re.search(r'\.\.\.$', text):
        return False
    return bool(re.search(r'[.!?]["\']?\s*$', text))


def starts_with_timecode(text):
    return bool(re.match(r'^(\d{1,2}:\d{2}\s*(a\.m\.|p\.m\.))', text.strip(), re.IGNORECASE))


def starts_with_dash(text):
    return text.strip().startswith('-')


def merge_subtitles(subs):
    blocks = []
    current_text = ""

    for sub in subs:
        clean = strip_tags(sub.text.strip().replace('\n', ' ')).strip()
        if not clean:
            continue

        if not current_text:
            current_text = clean
            continue

        if (not ends_sentence(current_text)) and (not starts_with_timecode(clean)) and (not starts_with_dash(clean)):
            current_text += " " + clean
        else:
            blocks.append(current_text.strip())
            current_text = clean

    if current_text:
        blocks.append(current_text.strip())

    return blocks


def translate_block_deepl(text, target_lang='RU'):
    try:
        result = translator.translate_text(text, target_lang=target_lang)
        return result.text
    except Exception as e:
        print(f"[!] Ошибка DeepL: {e}")
        return "Ошибка перевода"


async def translate_block_deepl_async(text, target_lang='RU'):
    # Запускаем синхронный вызов в отдельном потоке
    return await asyncio.to_thread(translate_block_deepl, text, target_lang)


async def translate_blocks(blocks, target_lang='RU'):
    results = []
    for block in async_tqdm(blocks, desc="🔁 Перевод DeepL"):
        translated = await translate_block_deepl_async(block, target_lang)
        results.append(translated)
    return results


def export_to_apkg(original_blocks, translated_blocks, out_path: Path, deck_name="Subtitle Translation"):
    print("📦 Экспорт в .apkg")

    model = genanki.Model(
        1607392319,
        'Subtitle Translation Model',
        fields=[
            {'name': 'Original'},
            {'name': 'Translation'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '{{Original}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{Translation}}',
            },
        ])

    deck = genanki.Deck(
        2059400110,
        deck_name
    )

    for orig, trans in zip(original_blocks, translated_blocks):
        note = genanki.Note(
            model=model,
            fields=[orig, trans]
        )
        deck.add_note(note)

    apkg_path = out_path.with_suffix(".apkg")
    genanki.Package(deck).write_to_file(str(apkg_path))
    print(f"✅ Файл .apkg сохранён: {apkg_path}")


def export_to_html(original_blocks, translated_blocks, out_path: Path):
    rows = []
    for orig, trans in zip(original_blocks, translated_blocks):
        orig_html = orig.replace('"', '&quot;')
        trans_html = trans.replace('"', '&quot;')
        rows.append(f"<tr><td>{orig_html}</td><td>{trans_html}</td></tr>")

    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Перевод субтитров</title>
        <style>
            body {{
                font-family: sans-serif;
                padding: 20px;
                background-color: #fdfdfd;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 10px;
                vertical-align: top;
                word-wrap: break-word;
            }}
            th {{
                background-color: #f0f0f0;
            }}
        </style>
    </head>
    <body>
        <h1>Перевод субтитров</h1>
        <table>
            <tr><th>Оригинал</th><th>Перевод</th></tr>
            {''.join(rows)}
        </table>
    </body>
    </html>
    """

    html_path = out_path.with_suffix(".html")
    html_path.write_text(html, encoding='utf-8')
    print(f"✅ HTML сохранён: {html_path}")


async def process_srt_to_html_blocks(src_path: Path, target_lang: str = 'RU'):
    print(f"🔍 Читаю файл: {src_path}")
    subs = pysrt.open(src_path, encoding='utf-8')

    print("🧠 Объединяю субтитры в логические блоки...")
    original_blocks = merge_subtitles(subs)
    print(f"📄 Найдено блоков для перевода: {len(original_blocks)}")

    translated_blocks = await translate_blocks(original_blocks, target_lang)

    export_to_html(original_blocks, translated_blocks, src_path)
    export_to_apkg(original_blocks, translated_blocks, src_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python3 translate_srt_deepl.py <файл.srt> [язык]")
        sys.exit(1)

    srt_file = Path(sys.argv[1])
    lang = sys.argv[2].upper() if len(sys.argv) > 2 else 'RU'

    asyncio.run(process_srt_to_html_blocks(srt_file, lang))
