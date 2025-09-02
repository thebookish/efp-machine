FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml /app/
RUN pip install --upgrade pip && pip install -e '.[dev]'
COPY . /app/
EXPOSE 8000
CMD ['uvicorn','app.main:app','--host','0.0.0.0','--port','8000']
