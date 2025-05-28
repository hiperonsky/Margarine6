import os
import subprocess


def send_video_to_user(
    bot, chat_id, user_id, username, url, video_path, width, height, admin_id
):
    try:
        # Получение размера файла
        file_size = os.path.getsize(video_path)
        file_size_mb = file_size / (1024 * 1024)

        # Если файл больше 50 МБ, разделяем его на части
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

            # Команда FFmpeg для деления файла
            output_template = os.path.join(parts_dir, f"{base_filename}_part%02d{ext}")
            ffmpeg_command = [
                "ffmpeg",
                "-i", video_path,
                "-c", "copy",
                "-map", "0",
                "-f", "segment",
                "-segment_time", "600",  # Делим на части по 10 минут
                "-reset_timestamps", "1",  # Сбрасываем тайм-коды
                output_template
            ]
            subprocess.run(ffmpeg_command, check=True)

            # Удаляем оригинальный файл после деления
            if os.path.exists(video_path):
                os.remove(video_path)
                print(f"Исходное видео {video_path} удалено после деления.")

            # Переименование частей с нумерацией от 01
            temp_parts = []
            for filename in os.listdir(parts_dir):
                if filename.startswith(base_filename + "_part") and filename.endswith(ext):
                    temp_parts.append(filename)
            temp_parts.sort()

            for idx, old_name in enumerate(temp_parts, start=1):
                new_name = f"{base_filename}_part{idx:02d}{ext}"
                old_path = os.path.join(parts_dir, old_name)
                new_path = os.path.join(parts_dir, new_name)
                os.rename(old_path, new_path)
                part_filenames.append(new_path)

            # Уведомление администратора о делении
            bot.send_message(
                admin_id,
                f"⚠️ Видео разделено на части:\n"
                f"ID: {user_id}\n"
                f"Имя: @{username}\n"
                f"Ссылка: {url}\n"
                f"Имя исходного файла: {original_filename} ({file_size_mb:.2f} MB)\n"
                f"Части:\n" +
                "\n".join(
                    [
                        f"{os.path.basename(part)} ({os.path.getsize(part) / (1024 * 1024):.2f} MB)"
                        for part in part_filenames
                    ]
                )
            )

            # Отправка частей пользователю
            for part_path in part_filenames:
                part_size_mb = os.path.getsize(part_path) / (1024 * 1024)
                if part_size_mb > 50:
                    bot.send_message(
                        chat_id,
                        f"⚠️ Одна из частей ({os.path.basename(part_path)}) превышает 50 МБ. "
                        f"Я не могу отправить её через Telegram."
                    )
                    continue  # Пропускаем часть, если она превышает лимит

                with open(part_path, 'rb') as video_file:
                    bot.send_video(chat_id, video_file, width=width, height=height)

                # Удаляем часть после отправки
                os.remove(part_path)
                print(f"Часть {part_path} отправлена и удалена.")
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
