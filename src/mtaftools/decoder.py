import struct
import wave
from pathlib import Path
from typing import List, Tuple

from .types import PathType
from .tables import STEP_SIZES, STEP_INDEXES
from .frame import FRAME_SIZE, FRAME_SAMPLES
from .header import HEADER_SIZE, HEADER_NAME
from .utils import clamp16
from .progress import Progress


def decode_frame_channel(
    frame: bytes,
    ch: int,
    hist: int,
    step_index: int,
) -> Tuple[List[int], int, int]:
    """
    Decode one channel of a frame using the MTAF ADPCM algorithm.

    The encoded nibble stream represents quantized differences that
    update the predictor (hist) using the current step index.

    Args:
        frame (bytes): Raw frame data.
        ch (int): Channel index (0 = left, 1 = right).
        hist (int): Initial predictor value for this channel.
        step_index (int): Initial ADPCM step index.

    Returns:
        Tuple[List[int], int, int]:
            Decoded PCM samples,
            final predictor value,
            final step index.
    """

    samples: List[int] = []

    # Extract nibble data for this channel
    nibble_data: bytes = frame[0x10 + 0x80 * ch : 0x10 + 0x80 * (ch + 1)]

    for i in range(FRAME_SAMPLES):

        # Each byte contains two 4-bit samples
        nibbles: int = nibble_data[i // 2]

        if i & 1:
            nibble: int = (nibbles >> 4) & 0xF
        else:
            nibble: int = nibbles & 0xF

        # Update predictor using step size table
        hist = clamp16(hist + STEP_SIZES[step_index][nibble])

        samples.append(hist)

        # Update step index based on nibble
        step_index += STEP_INDEXES[nibble]

        # Clamp step index to valid range
        if step_index < 0:
            step_index = 0
        elif step_index > 31:
            step_index = 31

    return samples, hist, step_index


def decode_mtaf_to_wav(input_path: PathType, output_path: PathType) -> None:
    """
    Decode an MTAF file into a stereo WAV file.

    The decoder reads frames sequentially, reconstructs PCM samples
    using the ADPCM predictor algorithm, then writes the result
    as 48kHz 16-bit stereo PCM.

    Args:
        input_path (PathType): Input MTAF file.
        output_path (PathType): Output WAV file.
    """

    input_path = Path(input_path)
    output_path = Path(output_path)

    with open(input_path, "rb") as f:

        # Read and validate file header
        header: bytes = f.read(HEADER_SIZE)

        if header[0:4] != HEADER_NAME:
            raise ValueError("Not an MTAF file")

        # Total number of samples stored in file
        total_samples: int = struct.unpack_from("<I", header, 0x5C)[0]

        # Calculate number of frames
        frames: int = (total_samples + FRAME_SAMPLES - 1) // FRAME_SAMPLES

        progress = Progress(total_samples)

        left_out: List[int] = []
        right_out: List[int] = []

        # ADPCM state for both channels
        hist_l: int = 0
        hist_r: int = 0
        step_l: int = 0
        step_r: int = 0

        for frame_index in range(frames):

            frame: bytes = f.read(FRAME_SIZE)

            if len(frame) < FRAME_SIZE:
                break

            # Read frame predictor/step values
            step_l = struct.unpack_from("<h", frame, 0x04)[0]
            step_r = struct.unpack_from("<h", frame, 0x06)[0]

            hist_l = struct.unpack_from("<h", frame, 0x08)[0]
            hist_r = struct.unpack_from("<h", frame, 0x0C)[0]

            # Clamp step indices (safety against malformed files)
            if step_l < 0:
                step_l = 0
            elif step_l > 31:
                step_l = 31

            if step_r < 0:
                step_r = 0
            elif step_r > 31:
                step_r = 31

            # Decode both channels
            l, hist_l, step_l = decode_frame_channel(frame, 0, hist_l, step_l)
            r, hist_r, step_r = decode_frame_channel(frame, 1, hist_r, step_r)

            left_out.extend(l)
            right_out.extend(r)

            # Update progress display
            processed_samples: int = min(
                (frame_index + 1) * FRAME_SAMPLES,
                total_samples
            )

            progress.update(processed_samples)

        progress.finish()

        # Remove padding samples from final frame
        left_out = left_out[:total_samples]
        right_out = right_out[:total_samples]

        # Interleave stereo samples
        interleaved: List[int] = []

        for l, r in zip(left_out, right_out):
            interleaved.append(l)
            interleaved.append(r)

        pcm: bytes = struct.pack(
            "<" + str(len(interleaved)) + "h",
            *interleaved
        )

    # Write WAV file
    with wave.open(str(output_path), "wb") as w:

        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(48000)

        w.writeframes(pcm)
