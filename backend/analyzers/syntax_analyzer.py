import ast


def analyze_syntax(code):
    try:
        ast.parse(code)

        return {
            "has_error": False,
            "error_type": None,
            "message": "No syntax errors found."
        }

    except SyntaxError as e:
        return {
            "has_error": True,
            "error_type": "SyntaxError",
            "message": e.msg,
            "line": e.lineno,
            "column": e.offset
        }