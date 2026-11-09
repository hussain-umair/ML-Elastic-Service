FROM python:3.11.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from torchvision.models import resnet18; resnet18(weights='IMAGENET1K_V1')"

COPY main.py .
COPY resnet_inference.py .

EXPOSE 8000 9001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]