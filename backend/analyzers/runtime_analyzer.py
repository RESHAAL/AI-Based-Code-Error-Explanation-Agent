import subprocess
import tempfile
import os
import re


def extract_error(stderr):
    lines = stderr.strip().splitlines()

    error_type = "RuntimeError"
    error_message = stderr.strip()
    line_number = None

    for line in reversed(lines):

        match = re.search(
            r'File ".*?", line (\d+), in',
            line
        )

        if match:
            line_number = int(match.group(1))

        error_match = re.search(
            r'([A-Za-z]+Error):\s*(.*)',
            line
        )

        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2)

    return {
        "type": error_type,
        "message": error_message,
        "line": line_number
    }


def analyze_runtime(code):
    temp_file = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as file:

            file.write(code)
            temp_file = file.name

        result = subprocess.run(
            ["python", temp_file],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:

            return {
                "has_error": False,
                "error_type": None,
                "message": "Code executed successfully.",
                "output": result.stdout,
                "line": None
            }

        error = extract_error(result.stderr)

        return {
            "has_error": True,
            "error_type": error["type"],
            "message": error["message"],
            "output": result.stdout,
            "line": error["line"]
        }

    except subprocess.TimeoutExpired:

        return {
            "has_error": True,
            "error_type": "TimeoutError",
            "message": "Code execution exceeded the 5-second limit.",
            "output": "",
            "line": None
        }

    except Exception as e:

        return {
            "has_error": True,
            "error_type": "ExecutionError",
            "message": str(e),
            "output": "",
            "line": None
        }

    finally:

        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)