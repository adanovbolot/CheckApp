FROM python:3.9.9

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y tesseract-ocr
RUN apt-get -y install cron && apt-get install gettext
RUN apt install -y libgl1-mesa-glx

COPY rus.traineddata /usr/share/tesseract-ocr/4.00/tessdata/
COPY eng.traineddata /usr/share/tesseract-ocr/4.00/tessdata/

COPY ./requirements.txt /usr/src/app/
RUN pip install -r requirements.txt

COPY . /usr/src/app/
