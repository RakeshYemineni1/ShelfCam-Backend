# services/model_runner.py
import os
import subprocess
from pathlib import Path

# app/services/model_runner.py
import subprocess
from pathlib import Path

def run_model_on_image(image_path: str, shelf_number: str = "A1") -> bool:
    script_path = Path(__file__).resolve().parent.parent.parent / "nmmodel" / "old1.py"
    
    # print("ROOT =", Path(__file__).resolve().parent.parent.parent)  # Inside model_runner.py
    # print("CHECK FILE =", (Path(__file__).resolve().parent.parent.parent / "NNMODEL" / "old1.py").exists())

    try:
        subprocess.run(
            ["python", str(script_path), image_path, shelf_number],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Model Error: {e.stderr}")
        return False

