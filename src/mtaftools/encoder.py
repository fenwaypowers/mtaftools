import struct
import wave
from pathlib import Path
from typing import List, Tuple

from .types import PathType
from .tables import STEP_SIZES, NEXT_STEP
from .frame import FRAME_SIZE, FRAME_SAMPLES
from .header import HEADER_SIZE, HEADER_NAME
from .utils import clamp16
from .progress import Progress
from .wavcheck import validate_wav_for_mtaf


def pack_nibbles(nibbles: List[int]) -> bytearray:

    out = bytearray(len(nibbles) // 2)

    j: int = 0
    for i in range(0, len(nibbles), 2):
        out[j] = nibbles[i] | (nibbles[i + 1] << 4)
        j += 1

    return out


def encode_channel_frame(
    samples: List[int],
    hist: int,
    step: int,
    step_sizes: List[List[int]],
) -> Tuple[List[int], int, int]:

    nibbles: List[int] = [0] * FRAME_SAMPLES

    for i in range(FRAME_SAMPLES):

        sample: int = samples[i]
        sizes: List[int] = step_sizes[step]

        best_n: int = 0
        best_err: int = 1 << 60
        best_hist: int = hist

        start: int = 0 if sample >= hist else 8
        end: int = start + 8

        for n in range(start, end):

            pred: int = clamp16(hist + sizes[n])
            err: int = abs(sample - pred)

            if err < best_err:
                best_err = err
                best_n = n
                best_hist = pred

        hist = best_hist
        step = NEXT_STEP[step][best_n]

        nibbles[i] = best_n

    return nibbles, hist, step


def encode_wav_to_mtaf(input_path: PathType, output_path: PathType) -> None:

    input_path = Path(input_path)
    output_path = Path(output_path)

    validate_wav_for_mtaf(input_path)

    w = wave.open(str(input_path), "rb")

    total_samples: int = w.getnframes()

    pcm = struct.unpack(
        "<" + str(total_samples * 2) + "h",
        w.readframes(total_samples),
    )

    left: List[int] = list(pcm[0::2])
    right: List[int] = list(pcm[1::2])

    frames: int = (total_samples + FRAME_SAMPLES - 1) // FRAME_SAMPLES

    progress = Progress(total_samples)

    with open(output_path, "wb") as f:

        header: bytearray = bytearray(HEADER_SIZE)
        header[0:4] = HEADER_NAME

        struct.pack_into("<I", header, 0x40, 0x44414548)
        struct.pack_into("<I", header, 0x5C, total_samples)

        header[0x61] = 1

        f.write(header)

        hist_l: int = 0
        hist_r: int = 0
        step_l: int = 0
        step_r: int = 0

        pos: int = 0

        step_sizes: List[List[int]] = STEP_SIZES

        for frame_index in range(frames):

            l: List[int] = left[pos:pos + FRAME_SAMPLES]
            r: List[int] = right[pos:pos + FRAME_SAMPLES]

            pos += FRAME_SAMPLES

            if len(l) < FRAME_SAMPLES:
                l += [0] * (FRAME_SAMPLES - len(l))
                r += [0] * (FRAME_SAMPLES - len(r))

            framebuf: bytearray = bytearray(FRAME_SIZE)

            struct.pack_into("<h", framebuf, 4, step_l)
            struct.pack_into("<h", framebuf, 6, step_r)

            struct.pack_into("<h", framebuf, 8, hist_l)
            struct.pack_into("<h", framebuf, 12, hist_r)

            ln, hist_l, step_l = encode_channel_frame(
                l, hist_l, step_l, step_sizes
            )

            rn, hist_r, step_r = encode_channel_frame(
                r, hist_r, step_r, step_sizes
            )

            framebuf[0x10:0x90] = pack_nibbles(ln)
            framebuf[0x90:0x110] = pack_nibbles(rn)

            f.write(framebuf)

            processed_samples: int = min(
                (frame_index + 1) * FRAME_SAMPLES,
                total_samples
            )

            progress.update(processed_samples)

    progress.finish()
