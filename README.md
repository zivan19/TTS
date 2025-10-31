# TTS

This repository now includes containerized tooling to make local development and
reproducible runs easier. The Docker image is based on the slim Python image,
installs `ffmpeg`, and installs this project so that the CLI and tests can run
without additional setup.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [GNU Make](https://www.gnu.org/software/make/)

## Make targets

The `Makefile` provides a set of convenience commands for common workflows:

| Command | Description |
| --- | --- |
| `make build` | Build the Docker image (`tts:latest` by default). |
| `make dev` | Build the image (if needed) and start an interactive shell inside it. |
| `make test` | Run the test suite inside the container (pass `PYTEST_ARGS="-k smoke"` to narrow the scope). |
| `make run FILE=book.txt OUT=out.wav` | Synthesize audio from `book.txt` and save the waveform to `out.wav`. |

You can override the default image tag by passing `IMAGE_NAME=my-tag make build`.
All commands mount the repository into `/workspace` within the container so that
changes on the host are immediately visible.

### Running inference

The `run` target expects a text file on the host machine and writes the
generated audio back to the host. For example:

```bash
make run FILE=samples/story.txt OUT=output/story.wav
```

Inside the container the target calls the `tts` CLI, reading the text file and
writing the audio output path you provide. The parent directory for `OUT` will
be created automatically and newline characters in the source text are flattened
before synthesis. Ensure the path supplied to `OUT` includes the desired filename
(e.g., `output.wav`).

### Running tests

```bash
make test
```

The tests execute with `pytest` inside the container. Additional arguments can
be forwarded with the `PYTEST_ARGS` variable:

```bash
make test PYTEST_ARGS="-k fast"
```

### Development shell

Run `make dev` to drop into a shell inside the container with the repository
mounted at `/workspace`. This is useful for one-off commands or debugging.
