FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary \
    torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY . .

EXPOSE 3008

CMD ["gunicorn", "server:app", "--bind", "0.0.0.0:3008", "--workers", "2", "--timeout", "300"]
