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

    Each sample is reconstructed from a 4-bit nibble that represents a
    quantized difference from the previous predictor value (hist).
    The difference is determined using the current ADPCM step index.

    Args:
        frame (bytes): Raw frame data containing channel ADPCM data.
        ch (int): Channel index within the frame (0 = first, 1 = second).
        hist (int): Initial predictor value (previous decoded sample).
        step_index (int): Initial ADPCM step index.

    Returns:
        Tuple[List[int], int, int]: Decoded PCM samples for this channel, final predictor value, and final step index.
    """

    samples: List[int] = []

    # Extract the 0x80-byte nibble block for this channel
    nibble_data = frame[0x10 + 0x80 * ch : 0x10 + 0x80 * (ch + 1)]

    for i in range(FRAME_SAMPLES):

        # Each byte stores two 4-bit samples
        nibbles = nibble_data[i // 2]

        if i & 1:
            nibble = (nibbles >> 4) & 0xF
        else:
            nibble = nibbles & 0xF

        # Apply ADPCM predictor update
        hist = clamp16(hist + STEP_SIZES[step_index][nibble])

        samples.append(hist)

        # Update step index using the nibble's step delta
        step_index += STEP_INDEXES[nibble]

        # Clamp step index to valid range
        if step_index < 0:
            step_index = 0
        elif step_index > 31:
            step_index = 31

    return samples, hist, step_index


def decode_mtaf_to_wav(input_path: PathType, output_path: PathType) -> None:
    """
    Decode an MTAF audio file into a WAV file.

    The decoder reads ADPCM frames sequentially, reconstructs PCM samples
    using the MTAF predictor algorithm, and writes the result as
    48 kHz 16-bit PCM audio.

    MTAF stores audio as multiple stereo tracks (2 channels per track).
    The total number of channels is determined by the track count stored
    in the file header.

    Args:
        input_path (PathType): Path to the input MTAF file.
        output_path (PathType): Path to the output WAV file.
    """

    input_path = Path(input_path)
    output_path = Path(output_path)

    with open(input_path, "rb") as f:

        # Read and validate file header
        header = f.read(HEADER_SIZE)

        if header[0:4] != HEADER_NAME:
            raise ValueError("Not an MTAF file")

        # Total number of PCM samples per channel
        total_samples = struct.unpack_from("<I", header, 0x5C)[0]

        # Number of stereo tracks stored in the file
        tracks = header[0x61]

        if tracks <= 0:
            tracks = 1

        channels = tracks * 2

        # Calculate number of ADPCM frames
        frames = (total_samples + FRAME_SAMPLES - 1) // FRAME_SAMPLES

        progress = Progress(total_samples)

        # Output buffers for each channel
        outputs: List[List[int]] = [[] for _ in range(channels)]

        # ADPCM predictor state for each channel
        hist: List[int] = [0] * channels
        step: List[int] = [0] * channels

        for frame_index in range(frames):

            # Each frame group contains one frame per stereo track
            for t in range(tracks):

                frame = f.read(FRAME_SIZE)

                if len(frame) < FRAME_SIZE:
                    break

                # Channel indices for this track
                ch_l = t * 2
                ch_r = ch_l + 1

                # Read predictor and step values from frame header
                step[ch_l] = struct.unpack_from("<h", frame, 0x04)[0]
                step[ch_r] = struct.unpack_from("<h", frame, 0x06)[0]

                hist[ch_l] = struct.unpack_from("<h", frame, 0x08)[0]
                hist[ch_r] = struct.unpack_from("<h", frame, 0x0C)[0]

                # Clamp step indices for safety
                step[ch_l] = max(0, min(31, step[ch_l]))
                step[ch_r] = max(0, min(31, step[ch_r]))

                # Decode both channels of the frame
                l, hist[ch_l], step[ch_l] = decode_frame_channel(
                    frame, 0, hist[ch_l], step[ch_l]
                )

                r, hist[ch_r], step[ch_r] = decode_frame_channel(
                    frame, 1, hist[ch_r], step[ch_r]
                )

                outputs[ch_l].extend(l)
                outputs[ch_r].extend(r)

            # Update progress indicator
            processed = min((frame_index + 1) * FRAME_SAMPLES, total_samples)
            progress.update(processed)

        progress.finish()

        # Remove padding samples from the final frame
        for ch in range(channels):
            outputs[ch] = outputs[ch][:total_samples]

        # Interleave samples for WAV output
        interleaved: List[int] = []

        for i in range(total_samples):
            for ch in range(channels):
                interleaved.append(outputs[ch][i])

        # Pack samples into 16-bit PCM
        pcm = struct.pack("<" + str(len(interleaved)) + "h", *interleaved)

    # Write decoded audio to WAV file
    with wave.open(str(output_path), "wb") as w:

        w.setnchannels(channels)
        w.setsampwidth(2)  # 16-bit samples
        w.setframerate(48000)

        w.writeframes(pcm)
