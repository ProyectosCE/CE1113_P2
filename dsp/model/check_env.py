"""Verifica que el entorno de Python de DSP esté listo para usarse.

Uso:
    python dsp/model/check_env.py
"""

import importlib
import sys

REQUIRED_PYTHON = (3, 11)
REQUIRED_MODULES = ["numpy", "scipy", "matplotlib"]


def main() -> int:
    ok = True

    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")
    if version[:2] < REQUIRED_PYTHON:
        print(f"  [ERROR] Se requiere Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]} o superior")
        ok = False

    # Dentro de un entorno virtual, sys.prefix es distinto de sys.base_prefix
    if sys.prefix == sys.base_prefix:
        print("  [AVISO] No hay un entorno virtual activo.")
        print("          Ejecute: source scripts/dsp/setup-env.sh")

    for name in REQUIRED_MODULES:
        try:
            module = importlib.import_module(name)
            print(f"  [OK]    {name} {module.__version__}")
        except ImportError:
            print(f"  [FALTA] {name}")
            ok = False

    print("Entorno listo." if ok else "El entorno tiene problemas.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())