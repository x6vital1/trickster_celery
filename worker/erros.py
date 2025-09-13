class MessageTimeout(Exception):
    def __init__(self, box_id: str, timeout_sec: int, attempt: int):
        self.box_id = box_id
        self.timeout_sec = timeout_sec
        self.attempts = attempt
        super().__init__(f"Box - {box_id} didn't receive message after {timeout_sec}s. Attempts: {attempt}")


