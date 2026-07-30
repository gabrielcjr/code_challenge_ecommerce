FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN chmod +x /app/.docker/entrypoint.sh

RUN npx @tailwindcss/cli -i ./static/css/src/input.css -o ./static/css/dist/output.css --minify || echo '@import "tailwindcss";' > ./static/css/dist/output.css

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

ENTRYPOINT ["/app/.docker/entrypoint.sh"]
