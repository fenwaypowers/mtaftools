import time


class Progress:

    def __init__(self, total_samples, sample_rate=48000, update_interval=0.2):
        self.total_samples = total_samples
        self.sample_rate = sample_rate
        self.update_interval = update_interval

        self.start_time = time.time()
        self.last_update = self.start_time

    def update(self, processed_samples):

        now = time.time()

        if now - self.last_update < self.update_interval:
            return

        elapsed = now - self.start_time

        percent = (processed_samples / self.total_samples) * 100

        audio_seconds = processed_samples / self.sample_rate

        speed = audio_seconds / elapsed if elapsed > 0 else 0.0

        print(
            f"{percent:6.2f}% | {elapsed:6.2f}s | {speed:5.2f}x",
            end="\r",
            flush=True,
        )

        self.last_update = now

    def finish(self):

        elapsed = time.time() - self.start_time
        audio_seconds = self.total_samples / self.sample_rate
        speed = audio_seconds / elapsed if elapsed > 0 else 0.0

        print(
            f"100.00% | {elapsed:6.2f}s | {speed:5.2f}x"
        )
