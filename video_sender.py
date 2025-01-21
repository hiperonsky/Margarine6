import os
import subprocess


def send_video_to_user(bot, chat_id, user_id, username, url, video_path, width, height, admin_id):
    try:
        # Получение размера файла
        file_size = os.path.getsize(video_path)
        file_size_mb = file_size / (1024 * 1024)

        # Проверка размера файла
        if file_size_mb > 50:
            # Уведомление пользователя о делении файла
            bot.send_message(
                chat_id,
                "Файл больше 50 МБ, попробую разделить его на несколько частей и отправить вам одну за другой."
            )

            # Деление файла на части
            parts_dir = os.path.dirname(video_path)
            original_filename = os.path.basename(video_path)
            base_filename, ext = os.path.splitext(original_filename)
            part_filenames = []

            # FFmpeg команда для деления файла
            ffmpeg_command = [
                "ffmpeg",
                "-i", video_path,
                "-c", "copy",
                "-map", "0",
                "-f", "segment",
                "-segment_time", "300",  # Пример: делим на 5-минутные части
                f"{parts_dir}/{base_filename}_part%03d{ext}"
            ]

            subprocess.run(ffmpeg_command, check=True)

            # Сбор имен файлов частей
            for filename in os.listdir(parts_dir):
                if filename.startswith(base_filename) and filename.endswith(ext):
                    part_filenames.append(filename)

            # Уведомление администратора о делении файла
            bot.send_message(
                admin_id,
                f"⚠️ Видео разделено на части:\n"
                f"ID: {user_id}\n"
                f"Имя: @{username}\n"
                f"Ссылка: {url}\n"
                f"Имя исходного файла: {original_filename} ({file_size_mb:.2f} MB)\n"
                f"Разделенные части:\n" +
                "\n".join(
                    [
                        f"{part} ({os.path.getsize(os.path.join(parts_dir, part)) / (1024 * 1024):.2f} MB)"
                        for part in part_filenames
                    ]
                )
            )

            # Отправка частей пользователю
            for part in part_filenames:
                part_path = os.path.join(parts_dir, part)
                with open(part_path, 'rb') as video_file:
                    bot.send_video(chat_id, video_file)
                os.remove(part_path)  # Удаляем отправленную часть
            return

        # Если файл меньше 50 МБ, отправляем как обычно
        with open(video_path, 'rb') as video_file:
            bot.send_video(chat_id, video_file, width=width, height=height)

        # Уведомление администратора о завершении
        bot.send_message(
            admin_id,
            f"✅ Видео успешно скачано и отправлено пользователю:\n"
            f"ID: {user_id}\n"
            f"Имя: @{username}\n"
            f"Ссылка: {url}\n"
            f"Имя файла: {os.path.basename(video_path)}\n"
            f"Размер файла: {file_size_mb:.2f} MB"
        )
    except subprocess.CalledProcessError as e:
        bot.send_message(admin_id, f"Ошибка при делении файла: {e}")
        raise
    except Exception as e:
        bot.send_message(admin_id, f"Ошибка при отправке видео: {e}")
        raise
    finally:
        # Удаление исходного видео
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"Видео {video_path} удалено.")
        else:
            print(f"Видео {video_path} не найдено для удаления.")
