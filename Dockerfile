FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir --no-deps -e . \
    && groupadd --gid 1000 hepatiq \
    && useradd --uid 1000 --gid 1000 --create-home hepatiq \
    && mkdir -p /app/data \
    && chown -R hepatiq:hepatiq /app

USER hepatiq

EXPOSE 8000 8501

CMD ["uvicorn", "hepatiq.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
