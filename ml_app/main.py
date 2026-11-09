import io
from fastapi import FastAPI, UploadFile, File
from resnet_inference import ModelInference
from PIL import Image
import psutil
import time
import threading
import os

from prometheus_client import Histogram, Gauge
from prometheus_client.exposition import start_http_server

PROMETHEUS_PORT = int(os.environ.get("PROMETHEUS_PORT", 9001))

RESPONSE_TIME = Histogram("ml_app_response_time_seconds", "Response time in seconds", ["endpoint"])
CPU_USAGE = Gauge("ml_app_cpu_usage_percent", "ML_APP CPU usage percentage")
MEMORY_USAGE = Gauge("ml_app_memory_usage_percent", "ML_APP memory usage percentage")

app = FastAPI()
model_inference = ModelInference()
start_http_server(PROMETHEUS_PORT)

def update_system_metrics():
    """Update CPU and memory usage metrics every second."""

    while True:
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent
            CPU_USAGE.set(cpu_usage)
            MEMORY_USAGE.set(memory_usage)
        except Exception as e:
            print(f"Error updating system metrics: {e}")
        time.sleep(1)

@app.on_event("startup")
async def startup_event():
    """Start the system metrics update thread on application startup."""

    threading.Thread(target=update_system_metrics, daemon=True).start()


@app.get("/")
async def home():
    """Endpoint to check if the ML app is running. Returns a welcome message."""

    return {"message": "Welcome to the ML App!"}

@app.middleware("http")
async def update_request_metrics(request, call_next):
    """Middleware to measure and record the response time for each request."""

    start_time = time.time()
    response = await call_next(request)

    RESPONSE_TIME.labels(endpoint=request.url.path).observe(time.time() - start_time)
    return response

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """Endpoint to handle prediction requests. It reads the uploaded image file, processes it, and returns the prediction result."""
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        preprocessed_image = model_inference.transform_image(image)
        prediction = model_inference.predict(preprocessed_image)
        return {"prediction": prediction}
    except Exception as e:
        return {"error": str(e)}