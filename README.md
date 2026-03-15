# mtaftools

Encode and decode the `adpcm_mtaf` audio format as used in KONAMI video games such as Metal Gear Solid 2 & 3 (Master/HD Collection versions).

## Features

- Convert `.mtaf` files to `.wav`.
- Convert stereo (2-channel) 48000 Hz 16-bit PCM `.wav` files to stereo `.mtaf` files.
- Currently only supports encoding to stereo (2-channel) `.mtaf`.
- Simple drag-and-drop support for `.exe` use
- Works as both a CLI tool and Python library, allowing for automation through python scripting

## How To Use

### Windows:

- Simply download the most recent `.exe` file from the [Releases tab](https://github.com/fenwaypowers/mtaftools/releases).
- To convert to `.wav`, drag your `.mtaf` file onto the `.exe`.
- To convert to `.mtaf`, drag your `.wav` file onto the `.exe`.

### Linux:

- Simply download the most recent binary from the [Releases tab](https://github.com/fenwaypowers/sdttools/releases).
- See the [Command-Line Use section](https://github.com/fenwaypowers/mtaftools?tab=readme-ov-file#command-line-use) to learn how to use the command line arguments.

You can also simply [install the package with Python](https://github.com/fenwaypowers/mtaftools#install-as-a-package) and use it on any computer that runs python.

## Command-Line Use

```
usage: mtaftools [-h] [-o OUTPUT] input

Encode/decode MTAF audio files used in Metal Gear Solid games.

Basic usage:
  mtaftools input.wav -o output.mtaf    Encode WAV to MTAF
  mtaftools input.mtaf -o output.wav    Decode MTAF to WAV

Drag-and-drop is supported when using the executable version.

positional arguments:
  input                Input file (.wav or .mtaf)

options:
  -h, --help           show this help message and exit
  -o, --output OUTPUT  Output file (optional)
```

## Install as a package

Make sure you have Python 3.9 or later installed.

Clone the repository and install locally:

```bash
git clone https://github.com/fenwaypowers/mtaftools
cd sdttools
pip install -e .
```

Example Python use:

```py
from mtaftools import encode_wav_to_mtaf, decode_mtaf_to_wav

# decode to wav
decode_mtaf_to_wav("input.mtaf", "output.wav")

# encode to mtaf
encode_wav_to_mtaf("input.wav", "output.wav")
```

## Credits

This project includes ideas and reference data derived from [vgmstream](https://github.com/vgmstream/vgmstream).

Copyright (c) 2008-2025 Adam Gashlin, Fastelbja, Ronny Elfert,
bnnm, Christopher Snowhill, NicknineTheEagle, bxaimc,
Thealexbarney, CyberBotX, et al

Used under the ISC-style license included here.

The MTAF ADPCM step tables and decoding behavior were derived
from the [vgmstream implementation](https://github.com/vgmstream/vgmstream/blob/master/src/coding/mtaf_decoder.c).

---

The MTAF container structure was derived from [FFmpeg](https://github.com/FFmpeg/FFmpeg)'s
[mtaf demuxer](https://www.ffmpeg.org/doxygen/3.3/mtaf_8c_source.html).

FFmpeg is licensed under LGPL 2.1 or later.

## License

[MIT](https://github.com/fenwaypowers/mtaftools/blob/main/LICENSE)

## Future Features

Future features:
- support encoding to channel count of more than 2

## Reporting Issues

When reporting bugs, please include:

- the command/code you ran
- the expected behavior
- the actual behavior
- the full error message
