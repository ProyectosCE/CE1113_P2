#!/usr/bin/env bash
# setup-env.sh
# Crea (si no existe) y activa el entorno virtual de Python para la parte DSP.
# Si faltan bibliotecas o cambió dsp/requirements.txt, las instala.
#
# Uso (desde cualquier carpeta del repositorio):
#     source scripts/dsp/setup-env.sh
#
# Para salir del entorno:
#     deactivate
#
# Variables opcionales:
#     PYTHON=python3.12 source scripts/dsp/setup-env.sh   # otro intérprete
#     DSP_FORCE_INSTALL=1 source scripts/dsp/setup-env.sh # reinstala todo

# El script debe cargarse con "source"; si se ejecuta con ./ el entorno
# se activaría en una subshell y se perdería al terminar.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: este script se debe cargar con 'source':"
    echo "    source scripts/dsp/setup-env.sh"
    exit 1
fi

_dsp_setup_env() {
    local script_dir repo_root venv_dir req_file stamp_file python_bin
    local req_hash old_hash

    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    repo_root="$(cd "$script_dir/../.." && pwd)"
    venv_dir="$repo_root/dsp/.venv"
    req_file="$repo_root/dsp/requirements.txt"
    stamp_file="$venv_dir/.requirements.sha256"
    python_bin="${PYTHON:-python3.11}"

    # 1. Elegir el intérprete: $PYTHON si se indicó; si no, python3.11,
    #    y si no existe, python3 siempre que sea versión 3.11 o superior
    python_bin="${PYTHON:-}"
    if [[ -z "$python_bin" ]]; then
        local candidate
        for candidate in python3.11 python3; do
            if command -v "$candidate" > /dev/null 2>&1 \
                && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
                python_bin="$candidate"
                break
            fi
        done
    fi

    if [[ -z "$python_bin" ]] || ! command -v "$python_bin" > /dev/null 2>&1; then
        echo "Error: no se encontró Python 3.11 o superior."
        echo "En Ubuntu 22.04: sudo apt install python3.11 python3.11-venv"
        echo "En Ubuntu 24.04: sudo apt install python3-venv"
        return 1
    fi

    # 2. Crear el entorno virtual si no existe
    if [[ ! -f "$venv_dir/bin/activate" ]]; then
        echo "[dsp] Creando entorno virtual en dsp/.venv con $python_bin..."
        if ! "$python_bin" -m venv "$venv_dir"; then
            echo "Error: no se pudo crear el entorno virtual."
            echo "En Ubuntu/Debian: sudo apt install python3.11-venv"
            return 1
        fi
    fi

    # 3. Activar el entorno
    # shellcheck disable=SC1091
    source "$venv_dir/bin/activate"

    # 4. Instalar dependencias si es la primera vez o si cambió requirements.txt
    req_hash="$(sha256sum "$req_file" | cut -d ' ' -f 1)"
    old_hash="$(cat "$stamp_file" 2> /dev/null)"

    if [[ "$req_hash" != "$old_hash" || -n "$DSP_FORCE_INSTALL" ]]; then
        echo "[dsp] Instalando dependencias de dsp/requirements.txt..."
        python -m pip install --quiet --upgrade pip \
            && python -m pip install --quiet -r "$req_file" \
            || { echo "Error: falló la instalación de dependencias."; return 1; }
        echo "$req_hash" > "$stamp_file"
    else
        echo "[dsp] Dependencias al día."
    fi

    echo "[dsp] Entorno activo: $(python --version) en dsp/.venv"
    echo "[dsp] Para salir: deactivate"
}

_dsp_setup_env
_dsp_status=$?
unset -f _dsp_setup_env
return $_dsp_status