# @title БЛОК 6: АВТОЗАГРУЗКА НА YOUTUBE (ДВУХКАНАЛЬНАЯ ОЧЕРЕДЬ + АВТОУДАЛЕНИЕ ОТРАБОТАННЫХ ФАЙЛОВ)
# =========================================================
import os, datetime, pickle, glob, re, shutil
from google.colab import drive
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

print("--- 6. ЗАПУСК YOUTUBE АВТОМАТИЗАЦИИ ---")

if not os.path.exists('/content/drive/MyDrive'): drive.mount('/content/drive')

root_dir = "/content/drive/MyDrive/Colab Notebooks/Project Meka Plays"
results_dir = os.path.join(root_dir, "Results")
done_dir = os.path.join(root_dir, "Done")
archive_dir = os.path.join(root_dir, "Archive")

just_upload_dir = os.path.join(root_dir, "Просто залить")

os.makedirs(just_upload_dir, exist_ok=True)
os.makedirs(archive_dir, exist_ok=True)

# Авторизация YouTube
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
creds = None
token_path = os.path.join(root_dir, 'token.pickle')
client_secrets_path = os.path.join(root_dir, 'client_secrets.json')

if os.path.exists(token_path):
    with open(token_path, 'rb') as token: creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        auth_url, _ = flow.authorization_url(prompt='consent')
        print(f"Перейдите по ссылке и скопируйте код: {auth_url}")
        creds = flow.fetch_token(code=input("Введите код: "))
    with open(token_path, 'wb') as token: pickle.dump(creds, token)

youtube = build("youtube", "v3", credentials=creds)
print("✅ Успешная авторизация в YouTube API!")

# СБОР ВСЕХ КАНДИДАТОВ НА ЗАЛИВКУ
candidates = []

# Канал 1: Обработанные ИИ проекты из папки Results + Done
all_results_folders = [os.path.join(results_dir, d) for d in os.listdir(results_dir)
                       if os.path.isdir(os.path.join(results_dir, d)) and not d.startswith("(Done)")]

for folder in all_results_folders:
    folder_name = os.path.basename(folder)
    video_path = os.path.join(done_dir, f"RESULT_{folder_name}.mkv")
    if not os.path.exists(video_path):
        video_path = os.path.join(done_dir, f"RESULT_{folder_name}.mp4")

    if os.path.exists(video_path):
        if os.path.exists(os.path.join(folder, "TIMESTAMPS_RAW.txt")) and not os.path.exists(os.path.join(folder, "TIMESTAMPS.txt")):
            continue

        archived_files = glob.glob(os.path.join(archive_dir, f"*{folder_name}*"))
        if archived_files:
            file_time = min(os.path.getmtime(f) for f in archived_files)
        else:
            vids = glob.glob(os.path.join(folder, "visual_chunks", "*.*"))
            file_time = min(os.path.getmtime(v) for v in vids) if vids else os.path.getmtime(folder)

        candidates.append({
            "type": "ai_processed",
            "video_path": video_path,
            "target_folder": folder,
            "original_name": folder_name,
            "time": file_time
        })

# Канал 2: Папка "Просто залить" (одиночные файлы без обработки)
just_upload_files = glob.glob(os.path.join(just_upload_dir, "*.mp4")) + glob.glob(os.path.join(just_upload_dir, "*.mkv"))
for file_path in just_upload_files:
    filename = os.path.basename(file_path)
    candidates.append({
        "type": "just_upload",
        "video_path": file_path,
        "target_folder": just_upload_dir,
        "original_name": os.path.splitext(filename)[0],
        "time": os.path.getmtime(file_path)
    })

if not candidates:
    print("\n🤷‍♂️ Очередь пуста! Нет готовых видео ни в Done, ни в папке 'Просто залить'.")
else:
    current_job = sorted(candidates, key=lambda x: x["time"])[0]

    video_path = current_job["video_path"]
    original_name = current_job["original_name"]

    print(f"📁 Найдена цель для публикации ({current_job['type']}): {os.path.basename(video_path)}")

    yt_title = original_name
    yt_desc = "Подпишись друг :)\nhttps://www.youtube.com/channel/UCzjOiJ1kSk4xqZFu9NX6n4A?sub_confirmation=1"

    if current_job["type"] == "ai_processed":
        timestamps_file = os.path.join(current_job["target_folder"], "TIMESTAMPS.txt")
        if os.path.exists(timestamps_file):
            with open(timestamps_file, "r", encoding="utf-8") as f:
                yt_desc += "\n\n" + f.read().strip()
                print("✅ ИИ-оглавление успешно прикреплено!")
    else:
        yt_desc += "\n\n00:00 приятного просмотра.."
        print("📝 Для прямого видео добавлено стандартное оглавление.")

    support_block = """

***

🌐 Поддержать криптовалютой (USDT):
(Пожалуйста, будьте внимательны с выбором сети при отправке, чтобы перевод не потерялся)
Деньги пойдут на покупку оборудования и развитие канала

Сеть TRC-20 (Tron):
TXqRfGxFQUUtaGU5FRA94e5UAL4qHz34bT

Сеть BEP-20 (BSC):
0x5e3499fde7dd023628aff25516cfaaad1b28363f

Огромное спасибо каждому за просмотры, лайки и любую поддержку! Это очень мотивирует двигаться дальше."""

    yt_desc += support_block

    if len(yt_title) > 100: yt_title = yt_title[:97] + "..."

    # Расчет календаря
    schedule_file = os.path.join(root_dir, "schedule.txt")
    if os.path.exists(schedule_file):
        with open(schedule_file, "r") as f: last_time_str = f.read().strip()
        last_time = datetime.datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
        publish_time = last_time + datetime.timedelta(days=1)
    else:
        publish_time = datetime.datetime.now() + datetime.timedelta(days=1)
        publish_time = publish_time.replace(hour=18, minute=0, second=0, microsecond=0)

    print(f"🗓 Запланировано на: {publish_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📺 Название на YouTube: {yt_title}")

    body = {
        "snippet": {
            "title": yt_title,
            "description": yt_desc,
            "categoryId": "20"
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_time.isoformat() + "Z"
        }
    }

    media_body = MediaFileUpload(video_path, chunksize=16*1024*1024, resumable=True)

    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media_body
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress_percent = int(status.progress() * 100)
                print(f"\r⏳ Загрузка на YouTube... {progress_percent}%", end="", flush=True)

        print(f"\n✅ УСПЕШНО ЗАГРУЖЕНО! Ссылка: https://youtu.be/{response['id']}")

        with open(schedule_file, "w") as f:
            f.write(publish_time.strftime("%Y-%m-%d %H:%M:%S"))

        # 🎯 АВТОУДАЛЕНИЕ МУСОРА ИЗ ОБЛАКА ПРИ УСПЕШНОМ ФИНАЛЕ
        if current_job["type"] == "ai_processed":
            # 1. Удаляем тяжелый готовый RESULT-файл из папки Done
            if os.path.exists(video_path):
                os.remove(video_path)

            # 2. Удаляем всю рабочую папку проекта с чанками и логами из Results
            if os.path.exists(current_job["target_folder"]):
                shutil.rmtree(current_job["target_folder"])

            # 3. 🎯 НОВОЕ: Находим и удаляем оригинальный тяжелый исходный файл из Archive
            archived_originals = glob.glob(os.path.join(archive_dir, f"*{original_name}*"))
            for orig in archived_originals:
                try:
                    if os.path.exists(orig):
                        os.remove(orig)
                        print(f"🧹 Удален оригинал из Архива: {os.path.basename(orig)}")
                except Exception as e:
                    print(f"⚠️ Ошибка при удалении исходника {os.path.basename(orig)}: {e}")

            print(f"🧹 Очистка завершена: Рендерер, папка проекта и оригинальный исходник из Archive удалены.")
        else:
            # Удаляем чистый исходник из папки "Просто залить"
            if os.path.exists(video_path):
                os.remove(video_path)
            print(f"🧹 Очистка завершена: Исходный файл удален из папки 'Просто залить'.")

    except Exception as e:
        print(f"\n❌ Ошибка при загрузке: {e}")
