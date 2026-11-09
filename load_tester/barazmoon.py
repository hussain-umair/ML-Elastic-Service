import aiohttp
import time
from typing import List, Tuple
import numpy as np
from multiprocessing import Process, active_children, Value
import asyncio
from aiohttp import ClientSession, TCPConnector


class BarAzmoon:
    def __init__(self, *, workload: List[int], endpoint: str, http_method = "get", **kwargs):
        np.random.seed(42)
        self.endpoint = endpoint
        self.http_method = http_method
        self.__workload = (rate for rate in workload)
        self.__counter = 0
        self.kwargs = kwargs
        self.__success_counter = Value('i', 0)
    
    def start(self):
        total_seconds = 0
        for rate in self.__workload:
            total_seconds += 1
            self.__counter += rate
            generator_process = Process(target=self.target_process, args=(rate, self.__success_counter))
            generator_process.daemon = True
            generator_process.start()
            active_children()
            time.sleep(1)
        print("Spawned all the processes. Waiting to finish...")
        time.sleep(self.kwargs.get("timeout", 5))
        for p in active_children():
            p.terminate()
            p.join()
        
        print(f"total seconds: {total_seconds}")

        return self.__counter, self.__success_counter.value

    def target_process(self, count, success_counter: Value):
        count = asyncio.run(self.generate_load_for_second(count))
        with success_counter.get_lock():
            success_counter.value += count

    async def generate_load_for_second(self, count):
        async with ClientSession(connector=TCPConnector(limit=0)) as session:
            delays = np.cumsum(np.random.exponential(1 / (count), count))
            tasks = []
            for i in range(count):
                task = asyncio.create_task(self.predict(delays[i], session))
                tasks.append(task)
            results = await asyncio.gather(*tasks)
            return sum(results)
    
    async def predict(self, delay, session):
        await asyncio.sleep(delay)
        data_id, image_bytes = self.get_request_data()
        if image_bytes is None:
        # no data to send
          return 0

        form = aiohttp.FormData()
        form.add_field('file', image_bytes, filename='test.jpeg', content_type='image/jpeg')

        try:
            async with getattr(session, self.http_method)(self.endpoint, data=form) as response:
                response = await response.json(content_type=None)
                is_success = self.process_response(data_id, response)
                return 1 if is_success else 0
        except Exception as exc:
            print(exc)
            return 0
    
    def get_request_data(self) -> Tuple[str, str]:
        return None, None
    
    def process_response(self, data_id: str, response: dict):
        return True