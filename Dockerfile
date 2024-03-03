# AUTOPUBLISHER DOCKERFILE BASED ON AUTOPUBLISHER BASE IMAGE (DEBIAN TESTING)
# TO RUN SHELL IN IMAGE ENTER `docker run --entrypoint /bin/bash -it <image>`

ARG AUTOPUBLISHER_BASE
ARG PYTHON_311

FROM $PYTHON_311 AS builder

RUN python3.11 -m venv /usr/share/python3/app
RUN /usr/share/python3/app/bin/pip install -U setuptools wheel

# bump this number for invalidating installing dependencies
# cache for following layers
ENV DOCKERFILE_VERSION 1

COPY dist/ /mnt/dist
RUN /usr/share/python3/app/bin/pip install -r /mnt/dist/requirements.txt
RUN /usr/share/python3/app/bin/pip install /mnt/dist/*.whl

RUN find-libdeps /usr/share/python3/app > /usr/share/python3/app/pkgdeps.txt

########################################################################
FROM $AUTOPUBLISHER_BASE as release

COPY --from=builder /usr/share/python3/app /usr/share/python3/app
RUN xargs -ra /usr/share/python3/app/pkgdeps.txt apt-install
RUN find /usr/share/python3/app/bin/ -name 'autopublisher*' -exec ln -snf '{}' /usr/bin/ ';'

CMD ["autopublisher"]
