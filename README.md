# TTS Edge

Utilities for working with the TTS Edge toolkit. This repository now ships as a
standard Python package using a `src/` layout, making it easy to build and
install locally for experimentation or private distribution.

## Installation

You can install the package directly from the repository root using `pip`. This
will build the wheel automatically and place the console script `tts-edge` on
your `PATH`.

```bash
pip install .
```

To verify the installation and view the packaged version, run the CLI with the
`--version` flag:

```bash
tts-edge --version
```

## Building distributions

To create both a source distribution (`sdist`) and a wheel, first ensure the
[`build`](https://pypa-build.readthedocs.io/) tool is installed:

```bash
python -m pip install build
```

Then run the build process from the project root:

```bash
python -m build
```

The generated artifacts will be placed in the `dist/` directory and can be
installed locally with `pip install dist/<artifact>.whl` as needed.
