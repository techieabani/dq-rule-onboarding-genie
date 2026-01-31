import pynvml

def get_gpu_status():
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0) # Your GTX 1650
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        
        # Convert bytes to MB
        total = info.total / 1024**2
        used = info.used / 1024**2
        free = info.free / 1024**2
        
        return {
            "gpu_name": pynvml.nvmlDeviceGetName(handle),
            "total_mb": round(total, 2),
            "used_mb": round(used, 2),
            "free_mb": round(free, 2),
            "utilization_percent": round((used / total) * 100, 2)
        }
    except Exception as e:
        return {"error": str(e)}