# import variables from .env if CI_REGISTRY_ID is not defined
ifndef CI_REGISTRY_ID
ifneq (,$(wildcard .env))  # if exists file
include .env
endif
endif

ifndef CI_REGISTRY_ID
$(error CI_REGISTRY_ID is not set)
endif

CI_PROJECT_NAME ?= autopublisher
PROJECT_PATH := autopublisher

VERSION = $(shell poetry version -s)

PYTHON_VERSION = 3.11
BASE_TAG = base

CI_REGISTRY_SERVER = cr.yandex
CI_REGISTRY ?= $(CI_REGISTRY_SERVER)/$(CI_REGISTRY_ID)

AUTOPUBLISHER_BASE_IMAGE ?= $(CI_REGISTRY)/$(CI_PROJECT_NAME):$(BASE_TAG)
PYTHON_311_IMAGE ?= $(CI_REGISTRY)/python:$(PYTHON_VERSION)

CI_PROJECT_NAME ?= $(shell echo $(PROJECT_PATH) | tr -cd "[:alnum:]")
CI_REGISTRY_IMAGE ?= $(CI_REGISTRY)/$(CI_PROJECT_NAME)
DOCKER_TAG = $(shell echo $(VERSION) | tr '+' '-')


all:
	@echo "make build 		- Build a docker image"
	@echo "make lint 		- Syntax check with pylama"
	@echo "make test 		- Test this project"
	@echo "make format 		- Format project with ruff and black"
	@echo "make upload 		- Upload this project to the docker-registry"
	@echo "make clean 		- Remove files which creates by distutils"
	@echo "make purge 		- Complete cleanup the project"
	@exit 0


wheel:
	poetry build -f wheel
	poetry export -f requirements.txt -o dist/requirements.txt

build: clean wheel
	docker build \
			--build-arg="AUTOPUBLISHER_BASE=$(AUTOPUBLISHER_BASE_IMAGE)" \
			--build-arg="PYTHON_311=$(PYTHON_311_IMAGE)" \
			-t $(CI_REGISTRY_IMAGE):$(DOCKER_TAG) \
			--target release .

clean:
	rm -fr dist

clean-pyc:
	find . -iname '*.pyc' -delete

lint:
	poetry run ruff $(PROJECT_PATH) tests
	poetry run mypy $(PROJECT_PATH)

format:
	poetry run ruff $(PROJECT_PATH) tests --fix-only
	poetry run black $(PROJECT_PATH) tests

purge: clean clean-pyc
	py -r autopublisher

test:
	poetry run pytest

start: build
	DOCKER_IMAGE=$(CI_REGISTRY_IMAGE):$(DOCKER_TAG) \
	docker-compose -f docker-compose.dev.yml up --force-recreate --renew-anon-volumes --build

upload: build
	echo "Make upload"
	#docker push $(CI_REGISTRY_IMAGE):$(DOCKER_TAG)

develop: clean
	py -n 3.11 autopublisher
	poetry env use $(shell py -p autopublisher)/bin/python3.11
	poetry --version
	poetry env info
	poetry install
