import sys
from pathlib import Path
import pysrt
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from tqdm import tqdm


def strip_tags(text):
    return BeautifulSoup(text, "html.parser").get_text()

def translate_blocks(blocks, target_lang):
    translator = GoogleTranslator(source='auto', target=target_lang)
    result = []
    for block in tqdm(blocks, desc="🔁 Перевод"):
        try:
            translated = translator.translate(block)
        except Exception as e:
            print(f"[!] Ошибка при переводе: {e}")
            translated = "Ошибка перевода"
        result.append(translated)
    return result

def process_srt_to_html_blocks(src_path: Path, target_lang: str = 'ru'):
    print(f"🔍 Читаю файл: {src_path}")
    subs = pysrt.open(src_path, encoding='utf-8')

    original_blocks = []
    for sub in subs:
        raw_text = strip_tags(sub.text.strip())
        if raw_text:
            original_blocks.append(' '.join(raw_text.splitlines()))
        else:
            original_blocks.append("")

    print(f"📄 Найдено реплик: {len(original_blocks)}")
    translated_blocks = translate_blocks(original_blocks, target_lang)

    rows = []
    for orig, trans in zip(original_blocks, translated_blocks):
        orig_html = orig.replace('"', '&quot;')
        trans_html = trans.replace('"', '&quot;')
        rows.append(f"<tr><td>{orig_html}</td><td>{trans_html}</td></tr>")

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Subtitle Translation</title>
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
        <h1>Subtitle Translation</h1>
        <table>
            <tr><th>Original</th><th>Translation</th></tr>
            {''.join(rows)}
        </table>
    </body>
    </html>
    """

    out_path = src_path.with_suffix(".html")
    out_path.write_text(html, encoding='utf-8')
    print(f"✅ HTML сохранён: {out_path}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python3 translate_srt_to_html.py <файл.srt> [язык]")
        sys.exit(1)

    srt_file = Path(sys.argv[1])
    lang = sys.argv[2] if len(sys.argv) > 2 else 'ru'

    process_srt_to_html_blocks(srt_file, lang)
