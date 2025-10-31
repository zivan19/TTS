# TTS

Utilities for working with the Edge Text-to-Speech tooling.

## FFmpeg dependency

FFmpeg is required for audio processing. On import the package attempts to
locate the executable in the following order:

1. The standard lookup that `ffmpeg-python` performs (respects the
   ``FFMPEG_BINARY`` environment variable and the current ``PATH``).
2. A set of common installation locations for Windows, macOS, and Linux.
3. The ``FFMPEG_BIN`` environment variable, which can point to the binary or a
   directory that contains it.

If FFmpeg cannot be found an informative error is raised so the issue can be
resolved quickly.

### Installing FFmpeg

Use one of the following platform-specific package managers to install FFmpeg:

#### Windows

```powershell
choco install ffmpeg
# or
scoop install ffmpeg
```

#### macOS

```bash
brew install ffmpeg
```

#### Linux

```bash
# Debian / Ubuntu
sudo apt-get update && sudo apt-get install -y ffmpeg

# Fedora / CentOS / RHEL (requires EPEL on some distributions)
sudo yum install -y ffmpeg
```

After installation, run ``ffmpeg -version`` to verify it is available. If the
binary lives outside your ``PATH``, point the package at it with
``FFMPEG_BIN=/path/to/ffmpeg``.

## Environment doctor

Install the project in editable mode and run the diagnostics to confirm your
setup:

```bash
python -m pip install -e .
tts-edge doctor
```

The doctor command checks:

- Python version compatibility (>= 3.8).
- FFmpeg discovery.
- Write permissions in the current working directory.

Resolve any failing checks before using the rest of the toolkit.
