Install [PyInstaller](https://pyinstaller.org/en/stable/).

```bash
python -m pip install pyinstaller
```

Then, run:

```bash
pyinstaller --onefile -n mtaftools src/mtaftools/__main__.py
```

The binary should be in the `dist` folder.

This should hopefully work for whatever OS/architecture you're on.
