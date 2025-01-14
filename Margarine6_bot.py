import os
import telebot
from yt_dlp import YoutubeDL
import subprocess
import re

API_TOKEN = '7667567049:AAFz2iBVViSl4i-d3gZMALLFvWMDplVw3PI'
ADMIN_ID = 167815811  # Замените на ваш Telegram ID

bot = telebot.TeleBot(API_TOKEN)

DOWNLOAD_DIR = "./downloads"

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

CHANNEL_USERNAME = "@vovanradio"

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

def split_video(video_path):
    """
    Разделяет видео на части по 20 минут и возвращает список сегментов.
    """
    try:
        sanitized_video_path = sanitize_filepath(video_path)  # Очищаем путь
        file_size = os.path.getsize(sanitized_video_path) / (1024 * 1024)  # Размер в мегабайтах

        part_num = 1
        output_files = []
        segment_duration = 1200  # 20 минут в секундах

        # Получаем длительность видео с помощью ffprobe
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", sanitized_video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        total_duration_str = result.stdout.strip()  # Убираем символы новой строки
        total_duration = float(total_duration_str)  # Конвертируем в число (в секундах)

        # Если видео слишком короткое, просто вернем его без разделения
        if total_duration <= segment_duration:
            output_files = [sanitized_video_path]
            return output_files, total_duration
        
        # Выполняем команду для разделения на 20 минутные части
        split_command = [
            "ffmpeg", "-i", sanitized_video_path,
            "-c", "copy",  # Копируем без перекодирования
            "-map", "0",   # Сохраняем все потоки (видео, аудио)
            "-f", "segment",  # Формат сегментации
            "-segment_time", str(segment_duration),  # Время сегментации: 1200 секунд = 20 минут
            "-reset_timestamps", "1",  # Сбрасываем метки времени в каждом сегменте
            f"{sanitized_video_path}_part%03d.mp4"  # Формат имени частей
        ]
        
        print(f"Сегментация: {' '.join(split_command)}")
        subprocess.run(split_command, check=True)
        print("Сегментация завершена. Проверяем созданные сегменты...")
        
        # Собираем пути к частям
        part_num = 1
        while True:
            part_file = f"{sanitized_video_path}_part{part_num:03d}.mp4"
            if os.path.exists(part_file):
                output_files.append(part_file)
                part_num += 1
            else:
                break
        
        if not output_files:
            print("Не удалось найти сегменты. Убедитесь, что команда ffmpeg выполняется корректно.")
            raise FileNotFoundError("Не удалось найти сегменты видео.")

        return output_files, total_duration
        
    except Exception as e:
        raise RuntimeError(f"Ошибка при разделении видео: {e}")



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

def download_with_proxy(url):
    ydl_opts_with_proxy = {
        'format': 'bestvideo[height<=480][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<=480][vcodec^=avc1]',
        'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
        'merge_output_format': 'mp4',
        'socket_timeout': 30,
        'geo_bypass': True,
        'cookies': '/root/Margarine6_bot/cookies.txt',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    }

    with YoutubeDL(ydl_opts_with_proxy) as ydl:
        info = ydl.extract_info(url, download=True)
        sanitized_path = sanitize_filepath(ydl.prepare_filename(info))
        return sanitized_path

# Определяем ydl_opts
ydl_opts = {
    'format': 'bestvideo[height<=480][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<=480][vcodec^=avc1]',
    'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
    'merge_output_format': 'mp4',
    'socket_timeout': 30,
    'geo_bypass': True,
}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    notify_admin(message.from_user.id, message.from_user.username, message.text)
    
    # Приветственное сообщение
    bot.reply_to(message, "Привет! Отправь мне ссылку на видео, и я скачаю его для тебя")
    
    # Отправка видеоинструкции
    try:
        with open("margarine_intro.mp4", "rb") as video:
            bot.send_video(
                message.chat.id,
                video,
                caption="Посмотрите видеоинструкцию, чтобы узнать, как пользоваться ботом."
            )
    except Exception as e:
        bot.send_message(
            ADMIN_ID,
            f"⚠️ Ошибка при отправке видеоинструкции:\n\n"
            f"Пользователь: @{message.from_user.username} (ID: {message.from_user.id})\n"
            f"Ошибка: {e}"
        )

@bot.message_handler(commands=['show_downloads'])
def show_downloads(message):
    """
    Показывает список файлов в папке для скачивания.
    Только для администратора.
    """
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
    # Проверяем подписку
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
        with YoutubeDL(ydl_opts) as ydl:
            # Предварительное извлечение информации о видео
            info = ydl.extract_info(url, download=False)

            # Очистка названия видео
            clean_title = sanitize_filename(info['title'])

            # Формирование пути для сохранения файла
            file_path = os.path.join(DOWNLOAD_DIR, f"{clean_title}.mp4")

            # Удаляем файл, если он уже существует
            if os.path.exists(file_path):
                os.remove(file_path)

            # Скачиваем видео
            info = ydl.extract_info(url, download=True)
            video_path = sanitize_filepath(ydl.prepare_filename(info))

            # Обрабатываем видео
            fixed_video_path, width, height = process_video(video_path)

            # Проверяем размер видео и при необходимости разделяем
            file_size = os.path.getsize(fixed_video_path) / (1024 * 1024)  # Размер в мегабайтах
            print(f"Начинаем проверку видео: {fixed_video_path}, размер: {file_size:.2f} МБ")
            if file_size > 49:
                bot.reply_to(message, "О-оу, видео великовато, придётся его попилить на части. Попробую...")
                # Разделяем видео, если его размер больше 49 МБ
                video_parts, total_duration = split_video(fixed_video_path)
                print(f"Сегменты готовы: {video_parts}. Общее количество частей: {len(video_parts)}")
            else:
                video_parts = [fixed_video_path]  # Если видео меньше 49 МБ, не разделяем
                total_duration = 0

        # Отправляем каждую часть видео с информацией о времени, если видео разделяется
        for idx, part in enumerate(video_parts, start=1):
            if not os.path.exists(part):
                print(f"Сегмент не найден: {part}. Пропускаем.")
                continue  # Пропускаем отправку недоступного файла

            if total_duration > 0:
                start_time = (idx - 1) * 20  # Начало отрезка (в минутах)
                end_time = min(idx * 20, total_duration // 60)  # Конец отрезка
                caption = f"Часть {idx}: с {start_time} до {end_time} минут"
            else:
                caption = None  # Если видео не разделяется, не добавляем подписей

            with open(part, 'rb') as video_file:
                bot.send_video(
                    message.chat.id,
                    video_file,
                    width=width,
                    height=height,
                    caption=caption
                )

            # Уведомление администратору о размере отправленного видео
            file_size = os.path.getsize(part) / (1024 * 1024)  # Размер в мегабайтах
            bot.send_message(
                ADMIN_ID,
                f"Видео отправлено пользователю @{message.from_user.username} (ID: {message.from_user.id}).\n"
                f"Размер видео: {file_size:.2f} МБ"
            )

            # Удаляем временный файл
            os.remove(part)

    except Exception as e:
        # Лог ошибки для администратора
        error_log = (
            f"⚠️ Ошибка при скачивании видео:\n\n"
            f"Пользователь: @{message.from_user.username} (ID: {message.from_user.id})\n"
            f"Ссылка на видео: {url}\n"
            f"Ошибка: {e}"
        )
        bot.send_message(ADMIN_ID, error_log)

        # Уведомление пользователя об ошибке
        bot.reply_to(
            message,
            "К сожалению при скачивании этого видео произошла ошибка. "
            "Я отправлю отчёт об этом администратору бота."
        )


# Запуск бота
bot.polling()
