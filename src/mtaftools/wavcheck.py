import wave
from pathlib import Path
from typing import TypedDict, List

from .types import PathType


class WavFormatError(Exception):
    """
    Exception raised when a WAV file does not meet the required format for MTAF encoding.
    """
    pass


class WavInfo(TypedDict):
    """
    A TypedDict representing the basic format information of a WAV file.
    """
    channels: int
    samplerate: int
    bitdepth: int
    frames: int


def describe_wav(path: PathType) -> WavInfo:
    """
    Return basic WAV format information.
    
    Args:
        path (PathType): The path to the WAV file.
    Returns:
        WavInfo: A dictionary containing the WAV format information.
    """

    with wave.open(str(path), "rb") as w:
        return {
            "channels": w.getnchannels(),
            "samplerate": w.getframerate(),
            "bitdepth": w.getsampwidth() * 8,
            "frames": w.getnframes(),
        }


def validate_wav_for_mtaf(path: PathType) -> WavInfo:
    """
    Ensure the WAV file is compatible with the MTAF encoder.
    """

    path = Path(path)
    info: WavInfo = describe_wav(path)

    errors: List[str] = []

    if info["samplerate"] != 48000:
        errors.append("sample rate must be 48000 Hz")

    if info["bitdepth"] != 16:
        errors.append("bit depth must be 16-bit PCM")

    if info["channels"] != 2:
        errors.append("channel count must be 2")

    if errors:
        raise WavFormatError(format_error_message(path, info, errors))

    return info


def format_error_message(path: PathType, info: WavInfo, errors: List[str]) -> str:
    """
    Format a detailed error message for an invalid WAV file.
    Args:
        path (PathType): The path to the WAV file.
        info (WavInfo): The detected WAV format information.
        errors (List[str]): A list of specific problems found with the WAV file.
    Returns:
        str: A formatted error message.
    """

    msg: List[str] = []
    msg.append("Invalid WAV format detected.\n")

    msg.append(f"Input file: {path}")
    msg.append("")
    msg.append("Detected format:")
    msg.append(f"  Sample rate: {info['samplerate']}")
    msg.append(f"  Bit depth:   {info['bitdepth']}-bit")
    msg.append(f"  Channels:    {info['channels']}")
    msg.append("")

    msg.append("Required format:")
    msg.append("  48000 Hz, 16-bit PCM, 2 channels")
    msg.append("")

    msg.append("Problems found:")
    for e in errors:
        msg.append(f"  - {e}")

    msg.append("")
    msg.append("Convert using ffmpeg:")
    msg.append(
        f"  ffmpeg -i \"{path}\" -ar 48000 -c:a pcm_s16le converted.wav"
    )

    return "\n".join(msg)
