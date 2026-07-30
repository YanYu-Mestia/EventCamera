#!/usr/bin/env bash
set -euo pipefail

project_root="/mnt/d/EventPoseFinal"
conda_bin="/home/mestia/miniconda3/bin/conda"
environment_file="$project_root/environment/wsl/dhp19-environment.yml"

export CONDA_REMOTE_CONNECT_TIMEOUT_SECS=60
export CONDA_REMOTE_READ_TIMEOUT_SECS=300
export CONDA_REMOTE_MAX_RETRIES=10

if [[ ! -x "$conda_bin" ]]; then
    printf 'conda=missing %s\n' "$conda_bin" >&2
    exit 2
fi

"$conda_bin" env update \
    --name eventpose-dhp19 \
    --file "$environment_file" \
    --prune

"$conda_bin" run --name eventpose-dhp19 python -c '
import h5py
import matplotlib
import numba
import numpy
import pytest
import scipy

print("environment=ok eventpose-dhp19")
print(f"numpy={numpy.__version__}")
print(f"scipy={scipy.__version__}")
print(f"h5py={h5py.__version__}")
print(f"matplotlib={matplotlib.__version__}")
print(f"numba={numba.__version__}")
print(f"pytest={pytest.__version__}")
'
