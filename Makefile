ifneq ("$(wildcard .env)","")
include .env
export
endif

CI_PROJECT_NAME ?= autopublisher
PROJECT_PATH := autopublisher

VERSION = $(shell poetry version -s)

ifndef CI_REGISTRY_ID
$(error CI_REGISTRY_ID is not set)
endif

CI_REGISTRY_SERVER ?= cr.yandex
CI_REGISTRY ?= $(CI_REGISTRY_SERVER)/$(CI_REGISTRY_ID)

BASE = "base"

AUTOPUBLISHER_BASE = $(CI_REGISTRY)/autopublisher:$(BASE)
PYTHON_311 = $(CI_REGISTRY)/python:3.11

CI_PROJECT_NAMESPACE ?= python
CI_PROJECT_NAME ?= $(shell echo $(PROJECT_PATH) | tr -cd "[:alnum:]")
CI_REGISTRY_IMAGE ?= $(CI_REGISTRY)/$(CI_PROJECT_NAMESPACE)/$(CI_PROJECT_NAME)
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
	docker build -t $(CI_REGISTRY_IMAGE):$(DOCKER_TAG) \
		--build-arg AUTOPUBLISHER_BASE=$(AUTOPUBLISHER_BASE) \
		--build-arg PYTHON_311=$(PYTHON_311) \
		--target release .

clean:
	rm -fr dist

clean-pyc:
	find . -iname '*.pyc' -delete

lint:
	poetry run mypy $(PROJECT_PATH)
	poetry run ruff $(PROJECT_PATH) tests

format:
	poetry run ruff $(PROJECT_PATH) tests --fix-only
	poetry run black $(PROJECT_PATH) tests

purge: clean
	rm -rf ./.venv

pytest:
	poetry run pytest

local:
	# TODO: обновить команду, чтоб работала
	docker-compose -f docker-compose.dev.yml up --force-recreate --renew-anon-volumes --build

pytest-ci:
	poetry run pytest -v --cov $(PROJECT_PATH) --cov-report term-missing --disable-warnings --junitxml=report.xml
	poetry run coverage xml

upload: build
	docker push $(CI_REGISTRY_IMAGE):$(DOCKER_TAG)

develop: clean
	poetry -V
	poetry install
	poetry run pre-commit install
