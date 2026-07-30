# WSL data and training environment

WSL is the intended home for DHP19 parsing, voxel validation, PyTorch training, evaluation, and visualization. The shared project is `/mnt/d/EventPoseFinal`; datasets remain at `/mnt/d/DHP19` and `/mnt/d/DHP19_preprocessed`.

Run the read-only environment inventory:

```bash
bash /mnt/d/EventPoseFinal/environment/wsl/check_environment.sh
```

The currently observed `/home/mestia/miniconda3` base has Python 3.14.6, NumPy 2.4.4, and PyTorch 2.11.0+cu128 with CUDA available. OpenCV, MMEngine, and MMPose were not found in that base during organization. Installing a stable project-specific GPU environment is intentionally deferred until CUDA compatibility and the selected pose framework are reviewed.

Do not treat `/home/mestia/openeb` as the authoritative SDK checkout. Windows `D:\OpenEB_Dev\openeb` remains the verified OpenEB 5.2.0 installation.
