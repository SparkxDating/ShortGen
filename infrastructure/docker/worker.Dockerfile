FROM python:3.11-slim-bookworm

WORKDIR /MoneyPrinterTurbo
ENV PYTHONPATH="/MoneyPrinterTurbo:/MoneyPrinterTurbo/packages/shared:/MoneyPrinterTurbo/packages/video-engine:/MoneyPrinterTurbo/packages/ai-engine:/MoneyPrinterTurbo/packages/media-engine:/MoneyPrinterTurbo/packages/audio-engine"
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-saas.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-saas.txt

COPY . .
CMD ["python", "-m", "apps.worker.main"]
