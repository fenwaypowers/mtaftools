import argparse
from pathlib import Path

from .encoder import encode_wav_to_mtaf
from .decoder import decode_mtaf_to_wav


def build_parser():
    parser = argparse.ArgumentParser(
        prog="mtaftools",
        description="Encode/decode MTAF audio"
    )

    parser.add_argument(
        "input",
        help="Input file (.wav or .mtaf)"
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output file (optional)"
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        parser.error(f"File not found: {input_path}")

    ext = input_path.suffix.lower()

    # WAV -> MTAF
    if ext == ".wav":

        if args.output:
            output = Path(args.output)
        else:
            output = input_path.with_suffix(".mtaf")

        encode_wav_to_mtaf(input_path, output)

        print(f"Encoded: {output}")

    # MTAF -> WAV
    elif ext == ".mtaf":

        if args.output:
            output = Path(args.output)
        else:
            output = input_path.with_suffix(".wav")

        decode_mtaf_to_wav(input_path, output)

        print(f"Decoded: {output}")

    else:
        parser.error("Input must be .wav or .mtaf")
