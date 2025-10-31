IMAGE_NAME ?= tts:latest
CONTAINER_WORKDIR ?= /workspace
PYTEST_ARGS ?=
FILE ?=
OUT ?=

.PHONY: dev build test run

build:
	docker build -t $(IMAGE_NAME) .

dev: build
	docker run --rm -it \
		-v $(CURDIR):$(CONTAINER_WORKDIR) \
		-w $(CONTAINER_WORKDIR) \
		$(IMAGE_NAME) bash

test: build
	docker run --rm \
		-v $(CURDIR):$(CONTAINER_WORKDIR) \
		-w $(CONTAINER_WORKDIR) \
		$(IMAGE_NAME) pytest $(PYTEST_ARGS)

run: build
ifndef FILE
	$(error FILE is required. Usage: make run FILE=path/to/input.txt OUT=output.wav)
endif
ifndef OUT
	$(error OUT is required. Usage: make run FILE=path/to/input.txt OUT=output.wav)
endif
	docker run --rm \
		-v $(CURDIR):$(CONTAINER_WORKDIR) \
		-w $(CONTAINER_WORKDIR) \
		$(IMAGE_NAME) \
		bash -lc "mkdir -p \"$$(dirname $(OUT))\" && tts --text \"$$(tr '\n' ' ' < $(FILE))\" --out_path \"$(OUT)\""
