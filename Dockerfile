FROM python:3.12-slim AS backend
WORKDIR /srv/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./
ENV DATABASE_URL=sqlite:////data/evshield.db REAL_BMS_WRITES=false OTP_MODE=production
RUN mkdir -p /data
EXPOSE 8000
CMD ["sh","-c","alembic -c alembic.ini upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
