import argparse
from pathlib import Path

from .encoder import encode_wav_to_mtaf
from .decoder import decode_mtaf_to_wav


def build_parser() -> argparse.ArgumentParser:
    """
    Build the argument parser for the mtaftools CLI.
    Returns:
        argparse.ArgumentParser: The configured argument parser.
    """

    parser = argparse.ArgumentParser(
        prog="mtaftools",
        description=(
            "Encode/decode MTAF audio files used in Metal Gear Solid games.\n\n"
            "Basic usage:\n"
            "  mtaftools input.wav -o output.mtaf    Encode WAV to MTAF\n"
            "  mtaftools input.mtaf -o output.wav    Decode MTAF to WAV\n\n"
            "Drag-and-drop is supported when using the executable version."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("input", help="Input file (.wav or .mtaf)")

    parser.add_argument("-o", "--output", help="Output file (optional)")

    parser.add_argument(
        "-t", "--total-samples", type=int, help="Total samples (length of audio)"
    )

    return parser


def prompt_total_samples() -> int:
    """
    Prompt the user for total samples in a REPL loop.
    Pressing Enter returns 0.
    """
    while True:
        user_input = input(
            "Enter total samples (press Enter for same value as your input wav): "
        ).strip()

        if user_input == "":
            return 0

        try:
            return int(user_input)
        except ValueError:
            print("Invalid number. Please enter an integer or press Enter.")


def main() -> None:
    """
    Main entry point for the mtaftools CLI.
    """

    parser: argparse.ArgumentParser = build_parser()
    args: argparse.Namespace = parser.parse_args()

    input_path: Path = Path(args.input)

    if not input_path.exists():
        parser.error(f"File not found: {input_path}")

    ext: str = input_path.suffix.lower()

    # WAV -> MTAF
    if ext == ".wav":

        if args.total_samples is not None:
            total_samples: int = args.total_samples
        else:
            total_samples = prompt_total_samples()

        output: Path
        if args.output:
            output = Path(args.output)
        else:
            output = input_path.with_suffix(".mtaf")

        encode_wav_to_mtaf(input_path, output, total_samples=total_samples)

        print(f"Encoded: {output}")

    # MTAF -> WAV
    elif ext == ".mtaf":

        output: Path
        if args.output:
            output = Path(args.output)
        else:
            output = input_path.with_suffix(".wav")

        decode_mtaf_to_wav(input_path, output)

        print(f"Decoded: {output}")

    else:
        parser.error("Input must be .wav or .mtaf")
