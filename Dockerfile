FROM python:3.15.2-slim-trixie
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/matplotlib \
    TZ=UTC
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt && python -m pip check
COPY extract_losses.py ./
WORKDIR /data
ENTRYPOINT ["python", "/app/extract_losses.py"]
