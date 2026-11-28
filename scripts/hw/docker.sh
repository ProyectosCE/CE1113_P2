#!/usr/bin/env bash
# docker.sh
# Entorno de hardware en Docker con Verilator y cocotb (versiones fijas en
# scripts/hw/Dockerfile), para que todo el grupo use las mismas herramientas.
#
# Uso (desde cualquier carpeta del repositorio):
#     scripts/hw/docker.sh lint [módulo ...]   lint de Reproductor/ip igual que el CI
#                                              (sin módulos: todos)
#     scripts/hw/docker.sh shell               terminal dentro del contenedor
#     scripts/hw/docker.sh <comando ...>       cualquier otro comando dentro del contenedor
#
# La imagen se construye sola la primera vez (varios minutos, por Verilator) y
# otra vez solo si cambian el Dockerfile o dsp/requirements.txt. El repositorio
# se monta en /repo con el usuario actual, así que los archivos generados no
# quedan a nombre de root.
set -euo pipefail

DIR=$(cd "$(dirname "$0")" && pwd)
RAIZ=$(cd "$DIR/../.." && pwd)
REQ="$RAIZ/dsp/requirements.txt"

uso() {
    sed -n '6,10p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
}

[ $# -gt 0 ] || uso
command -v docker > /dev/null || { echo "Error: no se encontró docker." >&2; exit 1; }

# 1. Imagen: la etiqueta es el hash del Dockerfile y de requirements.txt
HASH=$(cat "$DIR/Dockerfile" "$REQ" | sha256sum | cut -c 1-12)
IMAGEN="ce1113-hw:$HASH"

imagen() {
    docker image inspect "$IMAGEN" > /dev/null 2>&1 && return
    echo "[hw] Construyendo la imagen $IMAGEN (la primera vez tarda varios minutos)..."
    local ctx
    ctx=$(mktemp -d)
    cp "$DIR/Dockerfile" "$ctx/"
    mkdir -p "$ctx/dsp"
    cp "$REQ" "$ctx/dsp/"
    docker build -t "$IMAGEN" "$ctx" || { rm -rf "$ctx"; exit 1; }
    rm -rf "$ctx"
}

# 2. Carpeta de trabajo: la misma en la que se llamó el script, dentro de /repo
case "$PWD/" in
    "$RAIZ"/*) TRABAJO="/repo${PWD#"$RAIZ"}" ;;
    *)         TRABAJO=/repo ;;
esac

correr() {
    local tty=()
    if [ -t 0 ] && [ -t 1 ]; then tty=(-it); fi
    imagen
    docker run --rm "${tty[@]}" --user "$(id -u):$(id -g)" \
        -v "$RAIZ:/repo" -w "$TRABAJO" "$IMAGEN" "$@"
}

# 3. Comandos
case "$1" in
    lint)
        shift
        ARCHIVOS=()
        if [ $# -eq 0 ]; then
            cd "$RAIZ"
            ARCHIVOS=(Reproductor/ip/*/*.sv)
        else
            for m in "$@"; do
                [ -f "$RAIZ/Reproductor/ip/$m/$m.sv" ] \
                    || { echo "Error: no existe Reproductor/ip/$m/$m.sv" >&2; exit 1; }
                ARCHIVOS+=("Reproductor/ip/$m/$m.sv")
            done
        fi
        # Mismo comando que el job lint-sv de .github/workflows/ci.yml
        TRABAJO=/repo
        correr bash -c '
            verilator --version
            fallas=0
            for sv in "$@"; do
                top=$(basename "$sv" .sv)
                if verilator --lint-only -Wall -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM \
                        --top-module "$top" "$sv"; then
                    echo "OK: $top"
                else
                    echo "FALLA: $top"
                    fallas=$((fallas + 1))
                fi
            done
            exit $fallas' lint "${ARCHIVOS[@]}"
        ;;
    shell)
        correr bash
        ;;
    -h | --help)
        uso
        ;;
    *)
        correr "$@"
        ;;
esac
