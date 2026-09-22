import ast


def analyze_code_context(code):
    try:
        tree = ast.parse(code)

        functions = []
        variables = []
        imports = []

        for node in ast.walk(tree):

            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "line": node.lineno
                })

            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    variables.append({
                        "name": node.id,
                        "line": node.lineno
                    })

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return {
            "success": True,
            "functions": functions,
            "variables": variables,
            "imports": imports
        }

    except SyntaxError:
        return {
            "success": False,
            "functions": [],
            "variables": [],
            "imports": []
        }