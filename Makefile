# import variables from .env
ifneq (,$(wildcard .env))  # if exists file
include .env
endif

CI_PROJECT_NAME ?= autopublisher
PROJECT_PATH := autopublisher

VERSION = $(shell poetry version -s)

PYTHON_VERSION = 3.11
CI_PROJECT_NAME ?= $(shell echo $(PROJECT_PATH) | tr -cd "[:alnum:]")


all:
	@echo "make clean           - Remove files which creates by distutils"
	@echo "make clean-deb       - Remove 'deb/' folder with .deb packages"
	@echo "make bootstrap       - Bootstrap Debian, install the necessary packages and install application"
	@echo "make build           - Bootstrap Debian, install build packages and create .whl and requirements.txt"
	@echo "make build-magick    - Build ImageMagick-7 '.deb' with '.pdf' format support"
	@echo "make deploy          - Rebuild and install application on the server"
	@echo "make develop         - Create a development environment and install the application into it"
	@echo "make format          - Format project with ruff and black"
	@echo "make lint            - Syntax check with ruff and mypy"
	@echo "make purge           - Complete cleanup the project"
	@echo "make rebuild         - Simply create .whl and requirements.txt"
	@echo "make test            - Test this project"
	@echo "make wheel           - Build application .whl and create requirements.txt"
	@exit 0


wheel:
	poetry build -f wheel
	poetry export -f requirements.txt -o dist/requirements.txt

clean:
	rm -fr build
	rm -fr dist

clean-deb:
	rm -fr deb

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

develop: clean
	py -n 3.11 autopublisher
	poetry env use $(shell py -p autopublisher)/bin/python3.11
	poetry --version
	poetry env info
	poetry install

build-magick: clean-deb
	mkdir -p deb
	fab --hosts $(APP_BUILD_HOST) --port $(APP_BUILD_PORT) -i $(APP_BUILD_SSH_KEY) build_magick

# install debian build system and build app
build: clean
	mkdir -p dist
	fab --hosts $(APP_BUILD_HOST) --port $(APP_BUILD_PORT) -i $(APP_BUILD_SSH_KEY) bootstrap_system_and_build_app

# simple rebuild .whl
rebuild: clean
	mkdir -p dist
	fab --hosts $(APP_BUILD_HOST) --port $(APP_BUILD_PORT) -i $(APP_BUILD_SSH_KEY) rebuild_app

bootstrap:
	fab --hosts $(APP_DEPLOY_HOST) --port $(APP_DEPLOY_PORT) -i $(APP_DEPLOY_SSH_KEY) bootstrap

deploy: rebuild
	fab --hosts $(APP_DEPLOY_HOST) --port $(APP_DEPLOY_PORT) -i $(APP_DEPLOY_SSH_KEY) deploy

stop-service:
	fab --hosts $(APP_DEPLOY_HOST) --port $(APP_DEPLOY_PORT) -i $(APP_DEPLOY_SSH_KEY) stop_service

restart-service:
	fab --hosts $(APP_DEPLOY_HOST) --port $(APP_DEPLOY_PORT) -i $(APP_DEPLOY_SSH_KEY) restart_service
