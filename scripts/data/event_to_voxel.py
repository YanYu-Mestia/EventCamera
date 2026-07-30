import numpy as np

def generate_voxel_grid(events, width, height, num_bins=5):
    """
    将事件转换为体素网格 (Voxel Grid)
    """
    voxel_grid = np.zeros((num_bins, height, width), dtype=np.float32)
    if len(events) == 0:
        return voxel_grid

    t_start = events['t'][0]
    t_end = events['t'][-1]
    dt = t_end - t_start
    if dt <= 0: return voxel_grid

    t_norm = (num_bins - 1) * (events['t'] - t_start) / dt
    
    for i in range(len(events)):
        x, y, p, t = events['x'][i], events['y'][i], events['p'][i], t_norm[i]
        polarity = 1 if p == 1 else -1
        
        t_idx = int(t)
        t_weight = t - t_idx
        
        # 填充张量
        voxel_grid[t_idx, y, x] += (1 - t_weight) * polarity
        if t_idx + 1 < num_bins:
            voxel_grid[t_idx + 1, y, x] += t_weight * polarity
            
    return voxel_grid

def main():
    # --- 核心改进：直接在内存生成数据，绕过文件读取 ---
    width, height = 1280, 720
    print(f"正在内存中模拟生成 50,000 个事件...")
    
    dtype = [('x', '<u2'), ('y', '<u2'), ('p', '<u1'), ('t', '<u8')]
    events = np.zeros(50000, dtype=dtype)
    events['x'] = np.random.randint(0, width, 50000)
    events['y'] = np.random.randint(0, height, 50000)
    events['p'] = np.random.randint(0, 2, 50000)
    events['t'] = np.sort(np.random.randint(0, 1000000, 50000))

    # --- 执行转换 ---
    tensor = generate_voxel_grid(events, width, height, num_bins=5)
    
    print("-" * 30)
    print(f"转换成功！")
    print(f"生成的张量形状 (C, H, W): {tensor.shape}")
    print(f"非零点数量: {np.count_nonzero(tensor)}")
    print("-" * 30)

if __name__ == "__main__":
    main()