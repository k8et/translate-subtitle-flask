import io
from pathlib import Path
from tempfile import NamedTemporaryFile
from flask import Flask, request, jsonify
import pysrt
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

app = Flask(__name__)
translator = GoogleTranslator(source="auto", target="ru")  # 💡 язык можно менять

# ---------- utils -----------------------------------------------------------

def strip_tags(text: str) -> str:
    """Удаляем HTML/BB-теги."""
    return BeautifulSoup(text, "html.parser").get_text()

def parse_srt(file_path: Path) -> list[dict]:
    """Читаем .srt и возвращаем [{index, text}] без тегов и переносов строк."""
    subs = pysrt.open(file_path, encoding="utf-8")
    items = []
    for sub in subs:
        clean = strip_tags(sub.text.strip())
        if clean:
            items.append(
                {
                    "index": sub.index,
                    "original": " ".join(clean.splitlines()),
                }
            )
    return items
BATCH_SIZE      = 25
MAX_CHARS_BATCH = 4500
def translate_items(items: list[dict], target_lang: str = "ru") -> None:
    """
    Переводим items батчами, чтобы не делать запрос на каждую реплику.
    Добавляем поле 'translation' к каждому item.
    """
    trans = GoogleTranslator(source="auto", target=target_lang)
    sep = "\n====\n"

    i = 0
    while i < len(items):
        batch_items = []
        char_count = 0

        # Формируем пачку по BATCH_SIZE и MAX_CHARS_BATCH
        while (len(batch_items) < BATCH_SIZE and i < len(items) and
               char_count + len(items[i]["original"]) + 1 < MAX_CHARS_BATCH):
            batch_items.append(items[i]["original"])
            char_count += len(items[i]["original"]) + 1
            i += 1

        # Перевод одним запросом
        try:
            translated_text = trans.translate(sep.join(batch_items))
            translations = translated_text.split(sep)
        except Exception as e:
            # на случай ошибки проставим заглушки
            translations = ["[translation error]" for _ in batch_items]
            print(f"[!] Ошибка перевода батча: {e}")

        # Записываем переводы в исходный массив
        for j, text in enumerate(translations):
            idx = i - len(batch_items) + j
            items[idx]["translation"] = text
# ---------- API -------------------------------------------------------------

@app.route("/translate", methods=["POST"])
def translate_endpoint():
    """
    curl -X POST -F "file=@my.srt" -F "lang=uk" http://localhost:5000/translate
    """
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400

    lang = request.form.get("lang", "ru")
    uploaded = request.files["file"]

    # Сохраняем во временный файл (pysrt требует путь)
    with NamedTemporaryFile(delete=False, suffix=".srt") as tmp:
        tmp.write(uploaded.read())
        tmp_path = Path(tmp.name)

    items = parse_srt(tmp_path)
    translate_items(items, lang)
    tmp_path.unlink(missing_ok=True)  # очистка

    return jsonify({"items": items})

# ---------- entrypoint ------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
