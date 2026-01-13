import subprocess
import os
from pathlib import Path


def run_otava(test_name, config_path, output_format="regressions_only"):
    
    config_path = str(Path(config_path).resolve())

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"OTAVA config not found: {config_path}")

    env = os.environ.copy()
    env["OTAVA_CONFIG"] = config_path
    result = subprocess.run(
        ["otava", "analyze", test_name, "--output", output_format],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, 
        text=True,
    )
    
    if result.returncode != 0:
        raise RuntimeError(
            f"otava analyze failed for {test_name}\n{result.stderr}"
        )

    stdout = result.stdout.strip()
    return stdout

def handle_regression_result(stdout):
    if "No regressions found" in stdout:
        return ""
    result=""
    for line in stdout.splitlines():
        if ":" in line:
            result+=line+"\n"
        else:
            result+="\n"        
    return result

