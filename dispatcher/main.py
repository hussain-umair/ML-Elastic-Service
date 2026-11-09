import httpx
import uuid
import asyncio
from io import BytesIO
import os
import time
import psutil

from fastapi import FastAPI, UploadFile, Request
from prometheus_client import Histogram, Gauge
from prometheus_client.exposition import start_http_server

from dispatcher import Dispatcher

dispatcher = Dispatcher()
app = FastAPI()

RESPONSE_TIME = Histogram("response_time_seconds", "Response time in seconds", ["endpoint"])
QUEUE_SIZE = Gauge("dispatcher_queue_size", "Current request in a dispatcher queue")
CPU_USAGE = Gauge("dispatcher_cpu_usage_percent", "dispatcher_cpu usage percentage")
MEMORY_USAGE = Gauge("dispatcher_memory_usage_percent", "dispatcher_memory usage percentage")

ML_APP_URL = os.environ.get("ML_SERVICE_URL", "http://localhost")
ML_APP_PORT = int(os.environ.get("PORT", "8000"))
PROMETHEUS_PORT = int(os.environ.get("PROMETHEUS_PORT", 9001))
HTTP_CLIENT = None

start_http_server(PROMETHEUS_PORT)

pending_requests = {}
asyncio_lock = asyncio.Lock()
workers_running = False

@app.on_event("startup")
async def startup_event():
    """Initialize the dispatcher and start the worker tasks."""

    global HTTP_CLIENT, workers_running
    workers_running = True

    HTTP_CLIENT = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0),
        # will increase max_keepalive_connections to match the number of worker      
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=10)
    )

    asyncio.create_task(worker("worker-1"))
    asyncio.create_task(worker("worker-2"))
    asyncio.create_task(worker("worker-3"))
    asyncio.create_task(worker("worker-4"))
    asyncio.create_task(worker("worker-5"))
    asyncio.create_task(worker("worker-6"))
    asyncio.create_task(worker("worker-7"))
    asyncio.create_task(worker("worker-8"))
    asyncio.create_task(worker("worker-9"))
    asyncio.create_task(worker("worker-10"))
    asyncio.create_task(update_system_metrics())
    print("Dispatcher started and workers are running.")

@app.on_event("shutdown")
async def shutdown_event():
    """Shut down the dispatcher and stop the worker tasks."""

    global workers_running, HTTP_CLIENT
    workers_running = False

    if HTTP_CLIENT:
        await HTTP_CLIENT.aclose()
        HTTP_CLIENT = None
    print("Dispatcher stopped and workers are shut down.")

@app.get("/")
async def home():
    """For health check and monitoring purposes."""

    return {"message": "Welcome to the Dispatcher!"}

async def update_system_metrics():
    """Update system metrics for Prometheus monitoring."""

    while True:
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent
            queue_size = await dispatcher.qsize()
            CPU_USAGE.set(cpu_usage)
            MEMORY_USAGE.set(memory_usage)
            QUEUE_SIZE.set(queue_size)
        except Exception as e:
            print(f"Error updating system metrics: {e}")
        await asyncio.sleep(1)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware to measure and record the response time for each request."""

    start_time = time.time()
    endpoint = request.url.path
    response = await call_next(request)

    RESPONSE_TIME.labels(endpoint=endpoint).observe(time.time() - start_time)
    return response

async def worker(worker_id):
    """Worker task that processes requests from the dispatcher queue."""
    
    while workers_running:
        try:
            request_queue = dispatcher.request_queue
            queue_item, request_id = await request_queue.get()

            # This is crutial to avoid already Timed out requests to send further to ML_APP
            if request_id not in pending_requests:
                print(f"Worker {worker_id} - Request ID {request_id[:8]} not found in pending_requests. Skipping.")
                continue
    
            result = await get_inference(queue_item)
            print(f"Worker {worker_id} got result: {result}")

            async with asyncio_lock:
                future = pending_requests.pop(request_id, None)

                if future and not future.done():
                    future.set_result(result.get('prediction'))
            
        except Exception as e:
            print(f"Error in worker {worker_id} - Error getting request from queue: {e}")
            async with asyncio_lock:
                future = pending_requests.pop(request_id, None)
                if future and not future.done():
                    future.set_exception(e)

    print(f"Worker {worker_id} stopped.")


@app.post("/predict")
async def predict(file: UploadFile):
    """Endpoint to handle prediction requests. It reads the uploaded image file, adds it to the dispatcher queue, and waits for the prediction result."""
    
    request_id = str(uuid.uuid4())
    await dispatcher.add_to_queue(file, request_id)
    queue_size = await dispatcher.qsize()

    future = asyncio.Future()

    async with asyncio_lock:
        pending_requests[request_id] = future

    try:
        prediction = await asyncio.wait_for(future, timeout=60) # may we should increase this timeout
        return {"prediction": prediction, 'queue_size': queue_size}
    except asyncio.TimeoutError:
        async with asyncio_lock:
            pending_requests.pop(request_id, None)
        print(f"Prediction timed out for request_id: {request_id[:8]}")
        return {'error': 'Prediction request timed out'}
    except Exception as e:
        print(f"Error processing prediction for request_id: {request_id[:8]} - {e}")
        return {'error': str(e)}

async def get_inference(queue_item):
    """Send the image to the ML app for inference and return the result."""

    img_buffer = BytesIO()

    queue_item.save(img_buffer, format="JPEG")
    files = {'file': ('image.jpg', img_buffer.getvalue(), 'image/jpeg')}
    img_buffer.close()
    
    
    response = await HTTP_CLIENT.post(f'{ML_APP_URL}:{ML_APP_PORT}/predict', files=files)
    response.raise_for_status()
    return response.json()