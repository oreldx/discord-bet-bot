FROM python:3.10

WORKDIR /usr/src/bot

COPY ./requirements.txt /bot/requirements.txt

RUN pip install --no-cache-dir -r /bot/requirements.txt

VOLUME /usr/src/bot

COPY . ./

CMD ["python", "bot.py"]