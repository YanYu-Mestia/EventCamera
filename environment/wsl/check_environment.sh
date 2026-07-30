#!/usr/bin/env bash
set -uo pipefail

project_root="/mnt/d/EventPoseFinal"
raw_root="/mnt/d/DHP19"
preprocessed_root="/mnt/d/DHP19_preprocessed"
python_bin="${1:-/home/mestia/miniconda3/bin/python}"

for required_path in "$project_root" "$raw_root" "$preprocessed_root"; do
    if [[ -e "$required_path" ]]; then
        printf 'path=ok %s\n' "$required_path"
    else
        printf 'path=missing %s\n' "$required_path"
    fi
done

if [[ ! -x "$python_bin" ]]; then
    printf 'python=missing %s\n' "$python_bin"
    exit 2
fi

"$python_bin" - <<'PY'
import importlib
import sys

print(f"python={sys.version.split()[0]}")
missing_core = []
for module in ("numpy", "torch"):
    try:
        imported = importlib.import_module(module)
        print(f"package=ok {module} {getattr(imported, '__version__', 'unknown')}")
    except Exception as exc:
        missing_core.append(module)
        print(f"package=missing {module} {exc}")

for module in ("cv2", "mmengine", "mmpose"):
    try:
        imported = importlib.import_module(module)
        print(f"optional=ok {module} {getattr(imported, '__version__', 'unknown')}")
    except Exception:
        print(f"optional=missing {module}")

try:
    import torch
    print(f"cuda_available={torch.cuda.is_available()}")
    print(f"cuda_build={torch.version.cuda}")
except Exception:
    pass

if missing_core:
    raise SystemExit(2)
PY
