import os
import re
import shutil
import subprocess
import tempfile


SUPPORTED_LANGUAGES = {
    "python",
    "c",
    "cpp"
}


def _error_result(
    error_type,
    message,
    line=None,
    output=""
):
    return {
        "has_error": True,
        "error_type": error_type,
        "message": message,
        "output": output,
        "line": line
    }


def _success_result(output=""):
    return {
        "has_error": False,
        "error_type": None,
        "message": "Code executed successfully.",
        "output": output,
        "line": None
    }


def _extract_line_number(text):
    """
    Attempts to extract a useful source-code line number
    from Python, C, or C++ compiler/runtime output.
    """

    if not text:
        return None

    patterns = [
        r'line (\d+)',
        r':(\d+):\d+:',
        r':(\d+):',
        r'\((\d+),\d+\)',
        r'\((\d+)\)'
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:
                return int(match.group(1))

            except ValueError:
                pass

    return None


def _classify_compiler_error(stderr):
    """
    Converts common compiler/runtime messages into
    a simplified error type.
    """

    text = stderr.lower()

    if "undefined reference" in text:
        return "LinkerError"

    if "undeclared" in text:
        return "NameError"

    if "not declared" in text:
        return "NameError"

    if "was not declared" in text:
        return "NameError"

    if "segmentation fault" in text:
        return "SegmentationFault"

    if "floating point exception" in text:
        return "ArithmeticError"

    if "error:" in text:
        return "CompilationError"

    return "ExecutionError"


def _check_compiler(command):
    """
    Checks whether a required compiler/interpreter
    exists on the user's system.
    """

    executable = command[0]

    return shutil.which(executable) is not None


def _run_process(
    command,
    cwd,
    timeout=8
):
    """
    Runs a process with a timeout.
    """

    try:

        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

    except subprocess.TimeoutExpired:

        return None


# ============================================================
# PYTHON
# ============================================================

def _run_python(code):

    python_command = ["python"]

    if not _check_compiler(
        python_command
    ):

        return _error_result(
            "EnvironmentError",
            "Python interpreter was not found on this system."
        )

    source_path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as file:

            file.write(code)
            source_path = file.name

        result = _run_process(
            [
                "python",
                source_path
            ],
            cwd=os.path.dirname(source_path)
        )

        if result is None:

            return _error_result(
                "TimeoutError",
                "Python execution exceeded the 8-second limit."
            )

        if result.returncode == 0:

            return _success_result(
                result.stdout
            )

        error_text = result.stderr.strip()

        error_type = "ExecutionError"

        match = re.search(
            r"([A-Za-z]+Error):",
            error_text
        )

        if match:
            error_type = match.group(1)

        return _error_result(
            error_type,
            error_text,
            _extract_line_number(error_text),
            result.stdout
        )

    finally:

        if (
            source_path
            and os.path.exists(source_path)
        ):

            os.remove(source_path)


# ============================================================
# C
# ============================================================

def _run_c(code):

    if not _check_compiler(
        ["gcc"]
    ):

        return _error_result(
            "EnvironmentError",
            "GCC compiler was not found. "
            "Install GCC and make sure gcc is available "
            "in the system PATH."
        )

    temp_dir = tempfile.mkdtemp(
        prefix="buglens_c_"
    )

    source_path = os.path.join(
        temp_dir,
        "main.c"
    )

    executable = os.path.join(
        temp_dir,
        "main_program"
    )

    try:

        with open(
            source_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(code)

        compile_result = _run_process(
            [
                "gcc",
                source_path,
                "-o",
                executable
            ],
            cwd=temp_dir
        )

        if compile_result is None:

            return _error_result(
                "TimeoutError",
                "C compilation exceeded the 8-second limit."
            )

        if compile_result.returncode != 0:

            stderr = compile_result.stderr.strip()

            return _error_result(
                _classify_compiler_error(stderr),
                stderr,
                _extract_line_number(stderr)
            )

        run_result = _run_process(
            [executable],
            cwd=temp_dir
        )

        if run_result is None:

            return _error_result(
                "TimeoutError",
                "C program execution exceeded the 8-second limit."
            )

        if run_result.returncode == 0:

            return _success_result(
                run_result.stdout
            )

        stderr = run_result.stderr.strip()

        return _error_result(
            _classify_compiler_error(stderr),
            stderr,
            _extract_line_number(stderr),
            run_result.stdout
        )

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# C++
# ============================================================

def _run_cpp(code):

    if not _check_compiler(
        ["g++"]
    ):

        return _error_result(
            "EnvironmentError",
            "G++ compiler was not found. "
            "Install G++ and make sure g++ is available "
            "in the system PATH."
        )

    temp_dir = tempfile.mkdtemp(
        prefix="buglens_cpp_"
    )

    source_path = os.path.join(
        temp_dir,
        "main.cpp"
    )

    executable = os.path.join(
        temp_dir,
        "main_program"
    )

    try:

        with open(
            source_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(code)

        compile_result = _run_process(
            [
                "g++",
                source_path,
                "-o",
                executable
            ],
            cwd=temp_dir
        )

        if compile_result is None:

            return _error_result(
                "TimeoutError",
                "C++ compilation exceeded the 8-second limit."
            )

        if compile_result.returncode != 0:

            stderr = compile_result.stderr.strip()

            return _error_result(
                _classify_compiler_error(stderr),
                stderr,
                _extract_line_number(stderr)
            )

        run_result = _run_process(
            [executable],
            cwd=temp_dir
        )

        if run_result is None:

            return _error_result(
                "TimeoutError",
                "C++ program execution exceeded the 8-second limit."
            )

        if run_result.returncode == 0:

            return _success_result(
                run_result.stdout
            )

        stderr = run_result.stderr.strip()

        return _error_result(
            _classify_compiler_error(stderr),
            stderr,
            _extract_line_number(stderr),
            run_result.stdout
        )

    finally:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )


# ============================================================
# MAIN MULTI-LANGUAGE FUNCTION
# ============================================================

def analyze_multilanguage_runtime(
    code,
    language
):
    """
    Executes supported source code.

    Supported:
        Python
        C
        C++
    """

    if not code or not code.strip():

        return _error_result(
            "InputError",
            "Please enter source code before execution."
        )

    normalized_language = (
        language
        .strip()
        .lower()
    )

    if normalized_language not in SUPPORTED_LANGUAGES:

        return _error_result(
            "LanguageError",
            (
                "Unsupported language. "
                "BugLens currently supports Python, C, and C++."
            )
        )

    if normalized_language == "python":
        return _run_python(code)

    if normalized_language == "c":
        return _run_c(code)

    if normalized_language == "cpp":
        return _run_cpp(code)

    return _error_result(
        "LanguageError",
        "Unsupported programming language."
    )