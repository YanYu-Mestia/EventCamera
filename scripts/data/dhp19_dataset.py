import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
import os

def events_to_voxel_grid_fast(events, num_bins=5, height=180, width=240):
    """ 纯张量并行化转换：干掉 for 循环，速度提升 10 倍以上 """
    if isinstance(events, np.ndarray):
        events = torch.from_numpy(events)
    
    voxel_grid = torch.zeros((num_bins, height, width), dtype=torch.float32)
    if len(events) == 0:
        return voxel_grid
    
    x = events[:, 0].long()
    y = events[:, 1].long()
    t = events[:, 2].float()
    p = events[:, 3].float() * 2.0 - 1.0  # 映射到 [-1, 1] 更有利于网络收敛
    
    t_min, t_max = t[0], t[-1]
    t_norm = (t - t_min) / (t_max - t_min) * (num_bins - 1) if t_max > t_min else torch.zeros_like(t)
        
    t_idx = torch.clamp(torch.floor(t_norm).long(), 0, num_bins - 2)
    t_weight = t_norm - t_idx.float()
    
    # 核心提速：用 3D 索引将双线性插值一次性轰入 GPU/CPU 内存
    voxel_grid.index_put_((t_idx, y, x), p * (1.0 - t_weight), accumulate=True)
    voxel_grid.index_put_((t_idx + 1, y, x), p * t_weight, accumulate=True)
            
    return voxel_grid

def read_aedat_fast(file_path, width=240, height=180):
    """ 极速二进制流解析 """
    with open(file_path, 'rb') as f:
        line = f.readline()
        while line.startswith(b'#'):
            line = f.readline()
        raw_data = f.read()
        
    data = np.frombuffer(raw_data, dtype=np.uint32)
    if len(data) == 0:
        return np.empty((0, 4))
        
    all_addr, all_ts = data[0::2], data[1::2]
    
    # 位移解压
    x = (all_addr >> 17) & 0x1FF
    y = (all_addr >> 22) & 0x1FF
    p = (all_addr >> 15) & 0x1
    
    # 过滤越界噪点
    valid_mask = (x < width) & (y < height)
    return np.stack([x[valid_mask], y[valid_mask], all_ts[valid_mask], p[valid_mask]], axis=1)

class DHP19AedatDataset(Dataset):
    def __init__(self, data_dir, num_bins=5, height=180, width=240):
        self.data_dir = data_dir
        self.num_bins = num_bins
        self.height = height
        self.width = width
        self.file_list = [f for f in os.listdir(data_dir) if f.endswith('.aedat')]
        
    def __len__(self):
        return len(self.file_list)

    def __getitem__(self, idx):
        file_path = os.path.join(self.data_dir, self.file_list[idx])
        events = read_aedat_fast(file_path, self.width, self.height)
        voxel_tensor = events_to_voxel_grid_fast(events, self.num_bins, self.height, self.width)
        label_3d_dummy = torch.zeros((13, 3), dtype=torch.float32)  # 骨骼标签占位
        return voxel_tensor, label_3d_dummy

if __name__ == "__main__":
    data_directory = "/mnt/d/DHP19/DVS_movies/S3/session1"
    
    if os.path.exists(data_directory):
        dataset = DHP19AedatDataset(data_directory, num_bins=5, height=180, width=240)
        dataloader = DataLoader(dataset, batch_size=1, shuffle=False)
        
        for voxels, labels in dataloader:
            print(f"极速版转换成功！Voxel Tensor 形状: {voxels.shape}")
            break