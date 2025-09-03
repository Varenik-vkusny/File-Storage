FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

CMD [ "uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8000" ]