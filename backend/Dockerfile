FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --only-binary :all: -r requirements.txt
COPY api/ ./api/
COPY autoria/ ./autoria/
COPY calificacion/ ./calificacion/
COPY dashboard/ ./dashboard/
COPY herramientas/ ./herramientas/
COPY identidad/ ./identidad/
COPY infraestructura/ ./infraestructura/
COPY ingesta/ ./ingesta/
COPY omr/ ./omr/
COPY worker/ ./worker/
COPY tests/ ./tests/
COPY pytest.ini ./
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
