FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Adicione esta linha para expor a porta que seu app usa
EXPOSE 5000

# Comando para iniciar o app
CMD ["python", "app.py"]
