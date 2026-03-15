import time


class Progress:
    """
    Simple progress tracker for encoding/decoding.
    Displays percentage, elapsed time, and processing speed.
    """

    def __init__(
        self,
        total_samples: int,
        sample_rate: int = 48000,
        update_interval: float = 0.2
    ) -> None:
        self.total_samples: int = total_samples
        self.sample_rate: int = sample_rate
        self.update_interval: float = update_interval

        self.start_time: float = time.time()
        self.last_update: float = self.start_time

    def update(self, processed_samples: int) -> None:
        """
        Update the progress display based on the number of processed samples.
        
        Args:
            processed_samples (int): The total number of audio samples processed so far.
        """

        now: float = time.time()

        if now - self.last_update < self.update_interval:
            return

        elapsed: float = now - self.start_time

        percent: float = (processed_samples / self.total_samples) * 100

        audio_seconds: float = processed_samples / self.sample_rate

        speed: float = audio_seconds / elapsed if elapsed > 0 else 0.0

        print(
            f"{percent:6.2f}% | {elapsed:6.2f}s | {speed:5.2f}x",
            end="\r",
            flush=True,
        )

        self.last_update = now

    def finish(self) -> None:
        """
        Finalize the progress display when processing is complete.
        """

        elapsed: float = time.time() - self.start_time
        audio_seconds: float = self.total_samples / self.sample_rate
        speed: float = audio_seconds / elapsed if elapsed > 0 else 0.0

        print(
            f"100.00% | {elapsed:6.2f}s | {speed:5.2f}x"
        )
