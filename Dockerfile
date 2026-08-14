FROM python:3.11-slim

WORKDIR /app

# Copia e instala dependências
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY backend/ /app/

# Expõe a porta
EXPOSE 8000

# Comando para rodar
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
