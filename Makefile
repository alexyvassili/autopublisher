# import variables from .env
ifneq (,$(wildcard .env))  # if exists file
include .env
endif

CI_PROJECT_NAME ?= autopublisher
PROJECT_PATH := autopublisher

VERSION = $(shell poetry version -s)

PYTHON_VERSION = 3.11

CI_PROJECT_NAME ?= $(shell echo $(PROJECT_PATH) | tr -cd "[:alnum:]")

VERSION_TAG = $(shell echo $(VERSION) | tr '+' '-')
INSTALL_PATH = /usr/local/share/$(CI_PROJECT_NAME)


all:
	@echo "make build 		- Build a docker image"
	@echo "make lint 		- Syntax check with pylama"
	@echo "make test 		- Test this project"
	@echo "make format 		- Format project with ruff and black"
	@echo "make upload 		- Upload this project to the docker-registry"
	@echo "make clean 		- Remove files which creates by distutils"
	@echo "make purge 		- Complete cleanup the project"
	@echo "make start 		- Run application"
	@exit 0


wheel:
	poetry build -f wheel
	poetry export -f requirements.txt -o dist/requirements.txt

clean-build:
	rm -fr build

clean: clean-build
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

develop: clean
	py -n 3.11 autopublisher
	poetry env use $(shell py -p autopublisher)/bin/python3.11
	poetry --version
	poetry env info
	poetry install


bootstrap-debian:
	cp debian/tools/* /usr/local/bin/
	sudo cp debian/config/sources.list /etc/apt/sources.list
	sudo apt-get update && sudo apt-get install -y aptitude
	sudo aptitude update && sudo aptitude upgrade -y
	sudo apt-install apt-transport-https openssl ca-certificates locales tzdata
	mkdir -p /usr/local/share/ca-certificates
	sudo update-ca-certificates
	export SSL_CERT_DIR="/etc/ssl/certs"
	apt-install wget curl vim procps


install-build-libs: bootstrap-debian
	sudo apt-install build-essential


build-magick: clean-build install-build-libs
	mkdir -p build/magick
	mkdir -p build/magick/imagemagick-7-full-7.1.1-27
	mkdir -p deb
	sudo apt-install -y bzip2 cairosvg gir1.2-pangocairo-1.0-dev gsfonts-other libbzip3-dev  \
         libdjvulibre-dev libdjvulibre21 libfontconfig-dev libfreetype-dev libfreetype6-dev  \
         libgif-dev libgs-dev libgvc6 libheif-dev libjpeg-dev libjpeg62 libjxl-dev libjxl-devtools  \
         liblcms2-dev liblqr-dev liblzma-dev libopenexr-dev libopenjp2-7-dev libpango1.0-dev  \
         libperl-dev libpng-dev libraqm-dev libraw-dev librsvg2-dev libtiff-dev libtiff5-dev  \
         libwebp-dev libwebpdemux2 libwebpmux3 libwmf-dev libxml2-dev libzip-dev libzstd-dev  \
         libzstd1 pango1.0-tools wmf
	cd build/magick && \
		wget https://github.com/ImageMagick/ImageMagick/archive/refs/tags/7.1.1-27.tar.gz -O ImageMagick-7.1.1-27.tar.gz && \
		tar -xvzf ImageMagick-7.1.1-27.tar.gz
	cd build/magick/ImageMagick-7.1.1-27 && \
	./configure --disable-shared --disable-installed --disable-openmp  \
                --prefix="$(shell pwd)/build/magick/imagemagick-7-full-7.1.1-27/usr/local"  \
                --without-x --with-gslib --with-modules --with-bzlib -with-djvu --with-dps --with-fontconfig  \
                --with-freetype --with-gslib --with-gvc --with-heic --with-jbig --with-jpeg --with-jxl  \
                --with-dmr --with-lcms --with-lqr --with-lzma --with-magick-plus-plus --with-openexr  \
                --with-openjp2 --with-pango --with-png --with-raqm --with-raw --with-rsvg --with-tiff  \
                --with-webp --with-wmf --with-xml --with-zip --with-zlib --with-zstd && \
    make && \
    make install


build-deb-magick: build-magick
	cp -R scripts/imagemagick/DEBIAN build/magick/imagemagick-7-full-7.1.1-27/
	dpkg-deb --build build/magick/imagemagick-7-full-7.1.1-27
	cp build/magick/imagemagick-7-full-7.1.1-27.deb deb/


bootstrap:
	fab bootstrap


deploy:
	fab deploy
