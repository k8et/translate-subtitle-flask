import requests

# 🔧 Настройки
url = 'http://localhost:5000/translate'  # адрес сервера
srt_path = 'source.srt'                 # путь к .srt файлу
target_lang = 'ru'                       # язык перевода

# 📤 Отправляем POST запрос с файлом
with open(srt_path, 'rb') as file:
    files = {'file': (srt_path, file, 'application/octet-stream')}
    data = {'lang': target_lang}
    response = requests.post(url, files=files, data=data)

# ✅ Проверка результата
if response.ok:
    result = response.json()
    print("✅ Перевод успешно получен!")
    for item in result['items']:
        print(f"{item['index']}. {item['original']} → {item['translation']}")
else:
    print(f"❌ Ошибка: {response.status_code}")
    print(response.text)
