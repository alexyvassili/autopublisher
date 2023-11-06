CI_PROJECT_NAME ?= $(shell python3.11 setup.py --name)

VERSION = $(shell python3.11 setup.py --version | tr '+' '-')
PROJECT_PATH := $(shell echo $(CI_PROJECT_NAME) | tr '-' '_')

#CI_REGISTRY ?= registry.yandex.net
#CI_PROJECT_NAMESPACE ?= autopublisher
#CI_PROJECT_NAME ?= $(shell echo $(PROJECT_PATH) | tr -cd "[:alnum:]")
#CI_BUILD_TOKEN ?= ''
#CI_REGISTRY_IMAGE ?= $(CI_REGISTRY)/$(CI_PROJECT_NAMESPACE)/$(CI_PROJECT_NAME)
#CI_REGISTRY_IMAGE_STAGE ?= $(CI_REGISTRY)/$(CI_PROJECT_NAMESPACE)/$(CI_PROJECT_NAME)/stage

LINTER_IMAGE ?= registry.yandex.net/edadeal/gitlab/dockers/python-base:pylama

all:
	@echo "make build           - Build a docker images"
	@echo "make lint            - Syntax check with pylama"
	@echo "make test            - Test this project"
	@echo "make upload          - Upload this project to the docker-registry"
	@echo "make develop         - Configure the development environment"
	@echo "make start           - Start service locally with docker compose"
	@echo "make start-rebuild   - Rebuild all images and start service locally with docker compose"
	@echo "make clean           - Remove files which creates by distutils"
	@echo "make purge           - Complete cleanup the project"
	@echo "make gray            - Reformat code with gray linter"
	@echo "make version         - Print package name and version"
	@exit 0



$(PROJECT_PATH)/version.py:
	python3.11 bump.py $(PROJECT_PATH)/version.py

bump: clean $(PROJECT_PATH)/version.py

sdist: bump
	python3.11 setup.py sdist

build:
	echo "Make build"
#	docker build -t $(CI_PROJECT_NAME):$(VERSION) .

clean:
	rm -fr *.egg-info dist $(PROJECT_PATH)/version.py

clean-pyc:
	find . -iname '*.pyc' -delete

lint:
	echo "Make lint"
#	docker run --workdir /app --rm -v $(shell pwd):/app:ro $(LINTER_IMAGE) \
#		pylama
#
purge: clean
	py -r autopublisher

test: clean clean-pyc sdist
	echo "Make test"






upload: sdist
	echo "Make upload"


develop: purge
	py -n 3.11 autopublisher
	~/.python3/venvs/autopublisher/bin/pip install -Ue '.[develop]'
