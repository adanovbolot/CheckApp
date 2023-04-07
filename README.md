## Как работает запуск проекта?

### Файлы для проекта:

1. Внутри файла "Dockerfile", собирается образ проекта. Собирает все зависимости из файла requirements.txt


2. Внури второго файла "docker-compose.yml" есть целый список инструментов для проекта. 

            1. Из "Dockerfile" берем собранный образ

            2. Из базы данных выбрали самый уникальный - "postgresql"

            3. Redis — резидентная система управления базами данных класса 

            4. Celery - асинхронная очередь задач или очередь заданий

            5. Nginx — веб-сервер и почтовый прокси-сервер

        так же docker-compose перенаправил данные на .env файл
    
3. Файле .env хранятся данные, а именно

        1. Секретный ключ проекта - SECRET_KEY

        2. Ваш email для отправки писем - EMAIL_HOST_USER

        3. Ваш пароль для email - EMAIL_HOST_PASSWORD

        4. Ключ от API sms.ru - API_KEY

        5. Программа-отладчик - DEBUG, для проверки сервиса на ошибки.

        6. Ваш хост проекта - DJANGO_ALLOWED_HOSTS

        7. Название вашей базы данных - POSTGRES_DB

        8. Здесь мы выбираем какую БД использовать - POSTGRES_ENGINE

        9. Имя вашего пользователя - POSTGRES_USER

        10. Пароль от вашего пользователя - POSTGRES_PASSWORD

        11. Ваш хост - POSTGRES_HOST

        12. Ваш порт - POSTGRES_PORT

## ЗАПУСК ПРОЕКТА

## 1. Собрать контейнер
   
    sudo docker-compose up --build -d

## 2. Зайти внутрь контейнера 
   
    sudo docker exec -it django bash

## 3. Загрузка и обновить crontab и остальное


      apt-get update && apt-get -y install cron && apt-get install -y gettext


## 4. Собрать все статические файлы

    python manage.py collectstatic

## 5. Создать админа для сервера
   
    python manage.py createsuperuser

## 6. Для проверки работы расписание валюты

      python manage.py crontab add
      python manage.py crontab show

## 7. Команда для установки распознавание текста

      apt-get install tesseract-ocr
   
      apt-get install tesseract-ocr-rus

## 8. Выйти из контейнера

    exit