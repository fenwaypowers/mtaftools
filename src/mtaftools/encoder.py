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


TRKP_TEMPLATE = bytes([
    # TRKP header
    0x54,0x52,0x4B,0x50, 0x68,0x00,0x00,0x00,

    # unknown
    0x00,0x00,0x00,0x00,

    # vol L/R + pan
    0x7F,0x7F,0x40,0x00,

    # padding
    0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x00,

    # volume ramp table
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,
    0x7F,0x00,0x7F,0x00,

    # FF tail
    0xFF,0xFF,0xFF,0xFF,
    0xFF,0xFF,0xFF,0xFF,
    0xFF,0xFF,0xFF,0xFF,
    0xFF,0xFF,0xFF,0xFF,
])


def pack_nibbles(nibbles: List[int]) -> bytearray:
    """
    Pack a sequence of 4-bit values into bytes.

    Two nibbles are packed into each byte:
        byte = low_nibble | (high_nibble << 4)

    Args:
        nibbles (List[int]): List of 4-bit values (0–15).

    Returns:
        bytearray: Packed nibble data.
    """

    # Allocate output buffer (2 nibbles per byte)
    out = bytearray(len(nibbles) // 2)

    j: int = 0
    for i in range(0, len(nibbles), 2):

        # Pack two 4-bit values into one byte
        out[j] = nibbles[i] | (nibbles[i + 1] << 4)

        j += 1

    return out


def encode_channel_frame(
    samples: List[int],
    hist: int,
    step: int,
    step_sizes: List[List[int]],
) -> Tuple[List[int], int, int]:
    """
    Encode one channel of a frame using the MTAF ADPCM algorithm.

    Each PCM sample is approximated using a predictor (hist) and a
    quantized difference determined by the current step index.

    The encoder searches for the nibble (0–15) that produces the
    smallest prediction error.

    Args:
        samples (List[int]): PCM samples for the frame.
        hist (int): Initial predictor (previous decoded sample).
        step (int): Initial ADPCM step index.
        step_sizes (List[List[int]]): Lookup table of step sizes.

    Returns:
        Tuple[List[int], int, int]:
            Encoded nibble values,
            final predictor value,
            final step index.
    """

    # Output nibble buffer (one nibble per sample)
    nibbles: List[int] = [0] * FRAME_SAMPLES

    for i in range(FRAME_SAMPLES):

        sample: int = samples[i]

        # Precomputed size table for current step
        sizes: List[int] = step_sizes[step]

        # Track best encoding candidate
        best_n: int = 0
        best_err: int = 1 << 60
        best_hist: int = hist

        # Optimization:
        # Only search positive deltas if sample >= predictor
        start: int = 0 if sample >= hist else 8
        end: int = start + 8

        # Test candidate nibbles
        for n in range(start, end):

            # Predicted sample after applying delta
            pred: int = clamp16(hist + sizes[n])

            # Absolute prediction error
            err: int = abs(sample - pred)

            if err < best_err:
                best_err = err
                best_n = n
                best_hist = pred

        # Update predictor and step index
        hist = best_hist
        step = NEXT_STEP[step][best_n]

        # Store encoded nibble
        nibbles[i] = best_n

    return nibbles, hist, step


def encode_wav_to_mtaf(input_path: PathType, output_path: PathType) -> None:
    """
    Encode a stereo 48kHz 16-bit WAV file into MTAF format.
    
    The audio is split into frames. Each frame encodes a fixed number
    of samples per channel using the ADPCM predictor algorithm.

    Args:
        input_path (PathType): Input WAV file.
        output_path (PathType): Output MTAF file.
    """

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

        # reserve space for header
        f.write(bytearray(HEADER_SIZE))

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

            # cumulative sample index
            sample_pos = (frame_index + 1) * FRAME_SAMPLES
            struct.pack_into("<I", framebuf, 0, sample_pos)

            # step indexes
            struct.pack_into("<h", framebuf, 4, step_l)
            struct.pack_into("<h", framebuf, 6, step_r)

            # predictors
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

        # Build final header

        data_size: int = frames * FRAME_SIZE
        file_size: int = HEADER_SIZE + data_size

        header = bytearray(HEADER_SIZE)

        # MTAF
        header[0:4] = HEADER_NAME

        # pseudo file size
        struct.pack_into("<I", header, 0x04, file_size - 8)

        # HEAD
        struct.pack_into(">I", header, 0x40, 0x48454144)
        struct.pack_into("<I", header, 0x44, 0xB0)

        # volume / pan defaults
        struct.pack_into("<I", header, 0x50, 0x7F)
        struct.pack_into("<H", header, 0x54, 0x40)

        # channel configuration
        struct.pack_into("<I", header, 0x4C, 0x10)

        # loop start/end
        struct.pack_into("<I", header, 0x58, total_samples)
        struct.pack_into("<I", header, 0x5C, total_samples)

        # frame size
        struct.pack_into("<I", header, 0x60, 0x110)

        # channel factor
        header[0x61] = 1

        frames = total_samples // 0x100

        # loop frame counts
        struct.pack_into("<I", header, 0x64, frames)
        struct.pack_into("<I", header, 0x68, frames)

        # loop flag
        struct.pack_into("<I", header, 0x70, 0)

        # DATA chunk
        struct.pack_into(">I", header, 0x7F8, 0x44415441)
        struct.pack_into("<I", header, 0x7FC, data_size)

        offset = 0xF8
        size = len(TRKP_TEMPLATE)

        for _ in range(16):
            header[offset:offset+size] = TRKP_TEMPLATE
            offset += size

        # write header
        f.seek(0)
        f.write(header)


    progress.finish()
