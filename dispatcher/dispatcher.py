import asyncio
import io
from PIL import Image

class Dispatcher:
    """A class to manage the request queue for image processing tasks."""

    def __init__(self):
        self.request_queue = asyncio.Queue()
        self.request = None

    async def qsize(self):
        """Return the current size of the request queue."""
        return self.request_queue.qsize()

    async def add_to_queue(self, request, request_id):
        """Add a new request to the queue for processing."""
        image_bytes = await request.read()
        image = Image.open(io.BytesIO(image_bytes))
        await self.request_queue.put((image, request_id))

        return self.request_queue