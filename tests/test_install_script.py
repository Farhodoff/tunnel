import os
import subprocess


def test_install_script_exists_and_syntax():
    script_path = os.path.join(os.path.dirname(__file__), "..", "install.sh")
    assert os.path.isfile(script_path), "install.sh must exist in project root"
    assert os.access(script_path, os.X_OK), "install.sh must be executable"

    # Validate bash syntax
    result = subprocess.run(["bash", "-n", script_path], capture_output=True, text=True)
    assert result.returncode == 0, f"Bash syntax check failed: {result.stderr}"
