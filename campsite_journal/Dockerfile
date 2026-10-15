FROM python:3.13-slim
ARG BUILD_VERSION
ARG BUILD_ARCH
LABEL io.hass.version="${BUILD_VERSION}" io.hass.type="app" io.hass.arch="${BUILD_ARCH}"
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-kor && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py mobile_access.py address_search.py campsite_search.py live_sync.py reservation_import.py config.yaml .
COPY static ./static
ENV JOURNAL_VERSION=${BUILD_VERSION} JOURNAL_DATA=/data/campsite-journal HA_INGRESS=1 PYTHONUNBUFFERED=1 TZ=Asia/Seoul
EXPOSE 8099 8098
CMD ["python", "app.py"]
