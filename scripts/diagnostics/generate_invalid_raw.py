import numpy as np

def generate_manual_raw():
    width, height = 1280, 720
    filename = "test_dummy.raw"
    n_events = 100000
    
    # 构造事件数据格式
    dtype = [('x', '<u2'), ('y', '<u2'), ('p', '<u1'), ('t', '<u8')]
    events = np.zeros(n_events, dtype=dtype)
    events['x'] = np.random.randint(0, width, n_events)
    events['y'] = np.random.randint(0, height, n_events)
    events['p'] = np.random.randint(0, 2, n_events)
    events['t'] = np.sort(np.random.randint(0, 1000000, n_events))
    
    # 定义标准文件头
    # 注意：这里的元数据非常重要，Reader 靠它来确定分辨率
    header = f"% version: 2\n% date: 2026-05-15 11:00:00\n% geometry: {width}x{height}\n"
    
    with open(filename, "wb") as f:
        # 先写文本头
        f.write(header.encode('ascii'))
        # 再写二进制数据
        f.write(events.tobytes())
    
    print(f"带文件头的模拟数据生成成功: {filename}")

if __name__ == "__main__":
    generate_manual_raw()