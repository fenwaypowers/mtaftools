import struct
import wave
from pathlib import Path

from .tables import STEP_SIZES, NEXT_STEP
from .frame import FRAME_SIZE, FRAME_SAMPLES, HEADER_SIZE


def clamp16(x):
    if x > 32767:
        return 32767
    if x < -32768:
        return -32768
    return x

# pack nibbles
def pack_nibbles(nibbles):

    out = bytearray(128)

    j = 0
    for i in range(0, 256, 2):
        out[j] = nibbles[i] | (nibbles[i + 1] << 4)
        j += 1

    return out


def encode_wav_to_mtaf(input_path, output_path):

    input_path = Path(input_path)
    output_path = Path(output_path)

    w = wave.open(str(input_path), "rb")

    if w.getnchannels() != 2:
        raise ValueError("MTAF encoder supports 2 channel layout only")

    if w.getframerate() != 48000:
        raise ValueError("MTAF requires 48kHz input")

    if w.getsampwidth() != 2:
        raise ValueError("MTAF requires 16-bit PCM")

    total_samples = w.getnframes()

    pcm = struct.unpack(
        "<" + str(total_samples * 2) + "h",
        w.readframes(total_samples),
    )

    left = list(pcm[0::2])
    right = list(pcm[1::2])

    frames = (total_samples + FRAME_SAMPLES - 1) // FRAME_SAMPLES

    with open(output_path, "wb") as f:

        header = bytearray(HEADER_SIZE)
        header[0:4] = b"MTAF"

        struct.pack_into("<I", header, 0x40, 0x44414548)
        struct.pack_into("<I", header, 0x5C, total_samples)

        header[0x61] = 1

        f.write(header)

        hist_l = 0
        hist_r = 0
        step_l = 0
        step_r = 0

        pos = 0

        step_sizes = STEP_SIZES

        for _ in range(frames):

            l = left[pos:pos + FRAME_SAMPLES]
            r = right[pos:pos + FRAME_SAMPLES]

            pos += FRAME_SAMPLES

            if len(l) < FRAME_SAMPLES:
                l += [0] * (FRAME_SAMPLES - len(l))
                r += [0] * (FRAME_SAMPLES - len(r))

            framebuf = bytearray(FRAME_SIZE)

            struct.pack_into("<h", framebuf, 4, step_l)
            struct.pack_into("<h", framebuf, 6, step_r)

            struct.pack_into("<h", framebuf, 8, hist_l)
            struct.pack_into("<h", framebuf, 12, hist_r)

            ln = [0] * FRAME_SAMPLES
            rn = [0] * FRAME_SAMPLES

            for i in range(FRAME_SAMPLES):

                # LEFT CHANNEL
                sample = l[i]
                sizes = step_sizes[step_l]

                best_n = 0
                best_err = 1 << 60
                best_hist = hist_l

                start = 0 if sample >= hist_l else 8
                end = start + 8

                for n in range(start, end):

                    pred = hist_l + sizes[n]
                    pred = clamp16(pred)

                    err = abs(sample - pred)

                    if err < best_err:
                        best_err = err
                        best_n = n
                        best_hist = pred

                hist_l = best_hist
                step_l = NEXT_STEP[step_l][best_n]

                ln[i] = best_n

                # RIGHT CHANNEL
                sample = r[i]
                sizes = step_sizes[step_r]

                best_n = 0
                best_err = 1 << 60
                best_hist = hist_r

                start = 0 if sample >= hist_r else 8
                end = start + 8

                for n in range(start, end):

                    pred = hist_r + sizes[n]
                    pred = clamp16(pred)

                    err = abs(sample - pred)

                    if err < best_err:
                        best_err = err
                        best_n = n
                        best_hist = pred

                hist_r = best_hist
                step_r = NEXT_STEP[step_r][best_n]

                rn[i] = best_n

            framebuf[0x10:0x90] = pack_nibbles(ln)
            framebuf[0x90:0x110] = pack_nibbles(rn)

            f.write(framebuf)
