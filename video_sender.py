import os


def send_video_to_user(bot, chat_id, user_id, username, url, video_path, width, height, admin_id):
    try:
        # Получение размера файла
        file_size = os.path.getsize(video_path)
        file_size_mb = file_size / (1024 * 1024)

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
    except Exception as e:
        bot.send_message(admin_id, f"Ошибка при отправке видео: {e}")
        raise

    finally:
        # Удаление видео после отправки
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"Видео {video_path} удалено.")
        else:
            print(f"Видео {video_path} не найдено для удаления.")
