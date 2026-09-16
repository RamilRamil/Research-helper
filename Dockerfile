FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV GIT_PYTHON_REFRESH=quiet

COPY app/ ./app/
COPY scripts/eval_ragas.py ./scripts/eval_ragas.py
COPY specs/012-ragas-eval/questions.txt ./specs/012-ragas-eval/questions.txt

CMD ["python", "-m", "app.bot.main"]