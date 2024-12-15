FROM python:3.10-slim
LABEL authors="vladl"

ENV FRONTEND_URL=https://chat-frontend-vlo.vercel.app

WORKDIR /app

COPY requirements.txt .

RUN python -m ensurepip --upgrade && \
    pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]