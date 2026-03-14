import struct
import wave
from pathlib import Path

from .tables import STEP_SIZES, STEP_INDEXES
from .frame import FRAME_SIZE, FRAME_SAMPLES

HEADER_SIZE = 0x800

def clamp16(x):
    if x > 32767:
        return 32767
    if x < -32768:
        return -32768
    return x


def decode_frame_channel(frame, ch, hist, step_index):
    """
    Decode one channel of a frame.
    """

    samples = []

    nibble_data = frame[0x10 + 0x80 * ch : 0x10 + 0x80 * (ch + 1)]

    for i in range(FRAME_SAMPLES):

        nibbles = nibble_data[i // 2]

        if i & 1:
            nibble = (nibbles >> 4) & 0xF
        else:
            nibble = nibbles & 0xF

        hist = clamp16(hist + STEP_SIZES[step_index][nibble])

        samples.append(hist)

        step_index += STEP_INDEXES[nibble]

        if step_index < 0:
            step_index = 0
        elif step_index > 31:
            step_index = 31

    return samples, hist, step_index


def decode_mtaf_to_wav(input_path, output_path):

    input_path = Path(input_path)
    output_path = Path(output_path)

    with open(input_path, "rb") as f:

        header = f.read(HEADER_SIZE)

        if header[0:4] != b"MTAF":
            raise ValueError("Not an MTAF file")

        total_samples = struct.unpack_from("<I", header, 0x5C)[0]

        frames = (total_samples + FRAME_SAMPLES - 1) // FRAME_SAMPLES

        left_out = []
        right_out = []

        hist_l = 0
        hist_r = 0
        step_l = 0
        step_r = 0

        for _ in range(frames):

            frame = f.read(FRAME_SIZE)

            if len(frame) < FRAME_SIZE:
                break

            # frame header
            step_l = struct.unpack_from("<h", frame, 0x04)[0]
            step_r = struct.unpack_from("<h", frame, 0x06)[0]

            hist_l = struct.unpack_from("<h", frame, 0x08)[0]
            hist_r = struct.unpack_from("<h", frame, 0x0C)[0]

            if step_l < 0:
                step_l = 0
            elif step_l > 31:
                step_l = 31

            if step_r < 0:
                step_r = 0
            elif step_r > 31:
                step_r = 31

            l, hist_l, step_l = decode_frame_channel(frame, 0, hist_l, step_l)
            r, hist_r, step_r = decode_frame_channel(frame, 1, hist_r, step_r)

            left_out.extend(l)
            right_out.extend(r)

        # trim padding
        left_out = left_out[:total_samples]
        right_out = right_out[:total_samples]

        interleaved = []

        for l, r in zip(left_out, right_out):
            interleaved.append(l)
            interleaved.append(r)

        pcm = struct.pack("<" + str(len(interleaved)) + "h", *interleaved)

    with wave.open(str(output_path), "wb") as w:

        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(48000)

        w.writeframes(pcm)
