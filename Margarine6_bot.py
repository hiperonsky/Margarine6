import os
import telebot
from yt_dlp import YoutubeDL
import subprocess
import re
import config  # Импортируем модуль с константами

bot = telebot.TeleBot(API_TOKEN)

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def sanitize_filename(filename):
    """
    Удаляет из имени файла символы, которые могут вызывать конфликты.
    """
    return re.sub(r'[:"*?<>|/\\]', '', filename).strip()

def sanitize_filepath(filepath):
    """
    Применяет sanitize_filename ко всей части пути.
    """
    directory, filename = os.path.split(filepath)
    sanitized_filename = sanitize_filename(filename)
    return os.path.join(directory, sanitized_filename)

def notify_admin(user_id, username, message_text):
    bot.send_message(
        ADMIN_ID,
        f"🔔 Новый пользователь:\n"
        f"ID: {user_id}\n"
        f"Имя: {username}\n"
        f"Сообщение: {message_text}"
    )

def is_subscribed(user_id):
    """
    Проверяет, подписан ли пользователь на канал.
    """
    try:
        chat_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка при проверке подписки: {e}")
        return False

def process_video(video_path):
    try:
        video_path = sanitize_filepath(video_path)  # Убедимся, что путь безопасен
        fixed_video_path = sanitize_filepath(os.path.splitext(video_path)[0] + "_fixed.mp4")

        # Пересохранение видео с использованием FFmpeg (для исправления метаданных)
        ffmpeg_command = [
            "ffmpeg", "-i", video_path,
            "-movflags", "faststart",  # Исправление метаданных
            "-c", "copy",
            fixed_video_path
        ]
        subprocess.run(ffmpeg_command, check=True)

        # Получение размеров видео с помощью FFmpeg
        ffmpeg_command = [
            "ffmpeg", "-i", fixed_video_path
        ]
        result = subprocess.run(ffmpeg_command, stderr=subprocess.PIPE, text=True)
        ffmpeg_output = result.stderr

        # Используем регулярное выражение для извлечения ширины и высоты видео
        resolution_match = re.search(r'Video:.* (\d+)x(\d+)', ffmpeg_output)
        if resolution_match:
            width = int(resolution_match.group(1))
            height = int(resolution_match.group(2))
        else:
            raise ValueError("Не удалось извлечь размеры видео.")

        # Удаление оригинального видео (только если файл существует)
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"Оригинальное видео {video_path} удалено.")
        else:
            print(f"Оригинальное видео {video_path} не найдено для удаления.")

        return fixed_video_path, width, height

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ошибка при обработке видео через FFmpeg: {e}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    notify_admin(message.from_user.id, message.from_user.username, message.text)
    bot.reply_to(message, "Привет! Отправь мне ссылку на видео, и я скачаю его для тебя.")

@bot.message_handler(commands=['show_downloads'])
def show_downloads(message):
    if message.from_user.id == ADMIN_ID:
        try:
            files = os.listdir(DOWNLOAD_DIR)
            if files:
                bot.send_message(
                    message.chat.id,
                    "Содержимое папки downloads:\n" + "\n".join(files)
                )
            else:
                bot.send_message(message.chat.id, "Папка downloads пуста.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка при получении содержимого папки: {e}")
    else:
        bot.reply_to(message, "Эта команда доступна только администратору.")

@bot.message_handler(commands=['clean_downloads'])
def clean_downloads(message):
    """
    Очищает содержимое папки для скачивания.
    Только для администратора.
    """
    if message.from_user.id == ADMIN_ID:
        try:
            # Очищаем все файлы в папке downloads
            for filename in os.listdir(DOWNLOAD_DIR):
                file_path = os.path.join(DOWNLOAD_DIR, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            bot.send_message(message.chat.id, "Папка downloads очищена.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка при очистке папки: {e}")
    else:
        bot.reply_to(message, "Эта команда доступна только администратору.")

@bot.message_handler(content_types=['text'])
def download_video(message):
    if not is_subscribed(message.from_user.id):
        bot.reply_to(
            message,
            "Бот бесплатный, но работает только для подписчиков моего телеграм канала: "
            "[Передатчик Вована](https://t.me/+AM5qac1gwTUwMGNi)",
            parse_mode='Markdown'
        )
        return

    notify_admin(message.from_user.id, message.from_user.username, message.text)
    url = message.text
    bot.reply_to(message, "Начинаю загрузку видео...")

    try:
        with YoutubeDL({'format': 'best', 'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s'}) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = sanitize_filepath(ydl.prepare_filename(info))
            fixed_video_path, width, height = process_video(video_path)

            with open(fixed_video_path, 'rb') as video_file:
                bot.send_video(message.chat.id, video_file, width=width, height=height)
    except Exception as e:
        bot.send_message(ADMIN_ID, f"Ошибка при загрузке: {e}")
        bot.reply_to(message, "Произошла ошибка при загрузке видео.")

bot.polling()
