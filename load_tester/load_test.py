from pathlib import Path
from typing import Any, Tuple

from barazmoon import BarAzmoon


class MyLoadTester(BarAzmoon):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.image_path = Path(__file__).resolve().parent / "bla.jpeg"
        if not self.image_path.is_file():
            raise FileNotFoundError(
                f"could not find image file: {self.image_path}"
            )
    
        self.image_bytes = self.image_path.read_bytes()
        self.data_id = self.image_path.name


    def get_request_data(self) -> Tuple[str, str]:
        return self.data_id, self.image_bytes

    def process_response(self, sent_data_id: str, response: dict):
        # print(response.get("prediction"))
        if not isinstance(response, dict):
            print(f"Unexpected response for {sent_data_id}: {response}")
            return False

        labels = response.get("prediction")

        if not isinstance(labels, str):
            print(f"No valid label field returned for {sent_data_id}: {response}")
            return False
        print(response)
        print(f"{sent_data_id} -> {labels}")
        return True

workload_path = Path(__file__).resolve().parent / "workload.txt"
try:
    workload = [
        int(value)
        for value in workload_path.read_text(encoding="utf-8").split()
    ]
    # workload = [5]
except FileNotFoundError:
    raise FileNotFoundError(
        f"Could not find workload file: {workload_path}"
    )
if not workload:
    raise ValueError(f"Workload file is empty: {workload_path}")


# workload = [7, 12, 31]  # each item of the list is the number of request for a second
tester = MyLoadTester(workload=workload, endpoint="http://127.0.0.1:8001/predict", http_method="post")
tester.start()