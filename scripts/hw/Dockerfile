# Entorno de hardware del reproductor: Verilator y cocotb con versiones fijas.
# Se construye y se usa con scripts/hw/docker.sh (ver tests/hw/README.md).
#
# - Verilator se compila desde el código fuente: cocotb 2 necesita la 5.036 o
#   más nueva y el apt de Ubuntu 24.04 trae una anterior.
# - Python con cocotb y las bibliotecas del modelo DSP (dsp/requirements.txt),
#   para que los testbenches de cocotb puedan usar el modelo bit-exacto.
FROM ubuntu:24.04

ARG VERILATOR_VERSION=v5.040
ARG COCOTB_VERSION=2.0.1
# Compilaciones en paralelo de Verilator; más trabajos usan más memoria
ARG JOBS=4

ENV DEBIAN_FRONTEND=noninteractive

# Herramientas para compilar Verilator y para las simulaciones de cocotb
RUN apt-get update && apt-get install -y --no-install-recommends \
        autoconf bison ca-certificates flex g++ git help2man libfl-dev libfl2 \
        make perl python3 python3-dev python3-venv zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Verilator
RUN git clone --depth 1 --branch "$VERILATOR_VERSION" \
        https://github.com/verilator/verilator.git /tmp/verilator \
    && cd /tmp/verilator \
    && autoconf && ./configure && make -j"$JOBS" && make install \
    && cd / && rm -rf /tmp/verilator

# Python: cocotb y las dependencias del modelo DSP (incluye pytest)
COPY dsp/requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir "cocotb==$COCOTB_VERSION" -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# HOME en /tmp: el contenedor corre con el usuario del anfitrión, que no
# existe dentro de la imagen
ENV PATH="/opt/venv/bin:$PATH" \
    MPLBACKEND=Agg \
    HOME=/tmp

WORKDIR /repo
