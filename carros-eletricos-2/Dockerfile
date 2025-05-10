FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000-5002

CMD ["python", "server_a.py", "server_b.py", "server_c.py"]