# syntax=docker/dockerfile:1
#
# time eatmydata docker buildx build --progress=plain --tag disc/agar .
#

# ---- Debian ----
FROM mambaorg/micromamba:latest AS base

# activate base environment
ARG MAMBA_DOCKERFILE_ACTIVATE=1

WORKDIR /app

# dependencies
COPY --chown=$MAMBA_USER:$MAMBA_USER . .

# environment
# ENV LANG=C.UTF-8
# ENV TZ=America/Santiago
# ENV PATH=/opt/miniconda/bin:$PATH

# install base packages
RUN set -ex; \
    micromamba install --verbose --yes --name base --file /app/environment.yml && \
    micromamba clean --all --yes && \
    python -m spacy download en_core_web_sm

# run the flask app
CMD ["flask", "--app", "app", "run", "--host=0.0.0.0", "--port=5000", "--debug"]
