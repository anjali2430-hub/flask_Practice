# ── Stage: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

# Keeps Python from generating .pyc files and enables unbuffered stdout/stderr
# so logs appear immediately in docker logs / CloudWatch
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# The app listens on 5000; EC2 security group must allow inbound on this port
EXPOSE 5000

# --restart unless-stopped is set at docker run time (see pipeline deploy step)
# Gunicorn is production-grade; avoids Flask's single-threaded dev server
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
