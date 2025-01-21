import os


def send_video_to_user(bot, chat_id, user_id, username, url, video_path, width, height, admin_id):
    try:
        # Получение размера файла
        file_size = os.path.getsize(video_path)
        file_size_mb = file_size / (1024 * 1024)

        # Проверка размера видео
        if file_size_mb > 50:
            # Уведомление пользователя о превышении размера
            bot.send_message(
                chat_id,
                "К сожалению, это видео больше 50 мегабайт, и я пока не могу его вам отправить. "
                "Мы работаем над решением этой проблемы."
            )

            # Уведомление администратора
            bot.send_message(
                admin_id,
                f"⚠️ Видео не отправлено из-за превышения размера:\n"
                f"ID: {user_id}\n"
                f"Имя: @{username}\n"
                f"Ссылка: {url}\n"
                f"Имя файла: {os.path.basename(video_path)}\n"
                f"Размер файла: {file_size_mb:.2f} MB"
            )

            # Удаление файла
            if os.path.exists(video_path):
                os.remove(video_path)
                print(f"Видео {video_path} удалено (превышение размера).")
            return  # Завершаем выполнение функции

        # Отправка видео
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
        # Удаление видео после отправки (если оно еще существует)
        if os.path.exists(video_path):
            os.remove(video_path)
            print(f"Видео {video_path} удалено.")
        else:
            print(f"Видео {video_path} не найдено для удаления.")
