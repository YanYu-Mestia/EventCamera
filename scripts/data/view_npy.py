import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

npy_path = Path("/mnt/d/DHP19_preprocessed/S1/session1/mov1/frame_00001.npy")
output_dir = npy_path.parent / "viewed"
output_dir.mkdir(exist_ok=True)

data = np.load(npy_path)

print("shape:", data.shape)
print("dtype:", data.dtype)

for i, channel in enumerate(data):
    nonzero = channel[channel != 0]

    if len(nonzero) > 0:
        low, high = np.percentile(nonzero, [1, 99])
    else:
        low, high = 0, 1

    plt.figure(figsize=(8, 6))
    plt.imshow(channel, cmap="gray", vmin=low, vmax=high)
    plt.colorbar()
    plt.title(f"frame_00001 channel {i + 1}")
    plt.tight_layout()

    output_path = output_dir / f"frame_00001_channel_{i + 1}.png"
    plt.savefig(output_path, dpi=150)
    plt.close()

    print("saved:", output_path)
