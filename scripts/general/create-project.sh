#!/usr/bin/env bash
# Crea el proyecto Quartus (.qpf/.qsf) a partir de un sistema Platform Designer
# (.qsys, se genera su .qip) o de un .qip ya generado, mas el archivo de pines.
# No compila.  Uso: create-project.sh -t TOP -p pines.qsf [-q sistema.qsys] [-o dir] [otros.qip/.sdc/.v...]
exec "$(dirname "$(readlink -f "$0")")/build.sh" -C "$@"
