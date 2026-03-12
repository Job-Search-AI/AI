import os

def get_device(device_preference="auto"):
    """
    사용 가능한 device를 선택하는 함수
    
    Args:
        device_preference (str): "auto", "cuda", "mps", "cpu" 중 선택
        
    Returns:
        str: 선택된 device
    """
    import torch

    # 환경 변수에서 device 설정 확인
    env_device = os.getenv('DEVICE_PREFERENCE', None)
    if env_device:
        device_preference = env_device
        print(f"환경 변수에서 device 설정을 가져왔습니다: {env_device}")
    
    if device_preference == "auto":
        # CUDA가 사용 가능한지 확인
        if torch.cuda.is_available():
            return "cuda"
        # MPS가 사용 가능한지 확인 (Apple Silicon Mac)
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    elif device_preference == "cuda":
        if torch.cuda.is_available():
            return "cuda"
        else:
            print("CUDA를 사용할 수 없습니다. CPU를 사용합니다.")
            return "cpu"
    elif device_preference == "mps":
        if torch.backends.mps.is_available():
            return "mps"
        else:
            print("MPS를 사용할 수 없습니다. CPU를 사용합니다.")
            return "cpu"
    elif device_preference == "cpu":
        return "cpu"
    else:
        print(f"알 수 없는 device 설정: {device_preference}. CPU를 사용합니다.")
        return "cpu"

def print_device_info(device):
    """
    선택된 device 정보를 출력하는 함수
    
    Args:
        device (str): 선택된 device
    """
    import torch

    print(f"=== Device 정보 ===")
    print(f"선택된 device: {device}")
    
    if device == "cuda":
        print(f"CUDA 버전: {torch.version.cuda}")
        print(f"GPU 개수: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
    elif device == "mps":
        print("Apple Silicon Mac의 MPS 사용")
    elif device == "cpu":
        print("CPU 사용")
    
    print(f"PyTorch 버전: {torch.__version__}")
    print("=" * 20)

def set_device_preference(device_preference):
    """
    환경 변수에 device 설정을 저장하는 함수
    
    Args:
        device_preference (str): "auto", "cuda", "mps", "cpu" 중 선택
    """
    valid_devices = ["auto", "cuda", "mps", "cpu"]
    if device_preference in valid_devices:
        os.environ['DEVICE_PREFERENCE'] = device_preference
        print(f"Device 설정이 {device_preference}로 변경되었습니다.")
        print("이 설정은 현재 세션에만 적용됩니다.")
        print("영구적으로 설정하려면 shell 설정 파일에 추가하세요:")
        print(f"export DEVICE_PREFERENCE={device_preference}")
    else:
        print(f"잘못된 device 설정입니다. {valid_devices} 중에서 선택하세요.")
