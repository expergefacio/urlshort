FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir Flask gunicorn

COPY app.py /app/app.py

RUN mkdir -p /data

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]