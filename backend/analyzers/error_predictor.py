import ast


def predict_errors(code):
    """
    Performs lightweight static analysis to predict
    possible runtime errors before execution.
    """

    predictions = []

    try:
        tree = ast.parse(code)

    except SyntaxError:
        return {
            "success": False,
            "predictions": [
                {
                    "type": "SyntaxError",
                    "line": None,
                    "message": (
                        "Syntax error prevents static prediction."
                    )
                }
            ]
        }

    variable_types = {}
    variable_values = {}

    builtins_allowed = {
        "print",
        "len",
        "range",
        "int",
        "float",
        "str",
        "list",
        "dict",
        "set",
        "tuple",
        "bool",
        "sum",
        "min",
        "max",
        "abs",
        "enumerate",
        "zip",
        "input"
    }

    def infer_type(value):

        if isinstance(value, ast.Constant):

            if isinstance(value.value, str):
                return "str"

            if isinstance(value.value, bool):
                return "bool"

            if isinstance(value.value, int):
                return "int"

            if isinstance(value.value, float):
                return "float"

            if value.value is None:
                return "None"

        if isinstance(value, ast.List):
            return "list"

        if isinstance(value, ast.Tuple):
            return "tuple"

        if isinstance(value, ast.Dict):
            return "dict"

        if isinstance(value, ast.Set):
            return "set"

        return None

    # =====================================================
    # FIRST PASS — INFER SIMPLE VARIABLES
    # =====================================================

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):

            value_type = infer_type(node.value)

            constant_value = None

            if isinstance(
                node.value,
                ast.Constant
            ):
                constant_value = node.value.value

            for target in node.targets:

                if isinstance(
                    target,
                    ast.Name
                ):

                    variable_types[target.id] = value_type

                    if isinstance(
                        node.value,
                        ast.Constant
                    ):
                        variable_values[target.id] = (
                            constant_value
                        )

    # =====================================================
    # SECOND PASS — PREDICT ERRORS
    # =====================================================

    for node in ast.walk(tree):

        # =================================================
        # NAME ERROR
        # =================================================

        if isinstance(node, ast.Name):

            if isinstance(
                node.ctx,
                ast.Load
            ):

                if (
                    node.id not in variable_types
                    and node.id not in builtins_allowed
                ):

                    predictions.append({
                        "type": "NameError",
                        "line": node.lineno,
                        "message": (
                            f"'{node.id}' may be undefined "
                            "when this line executes."
                        )
                    })

        # =================================================
        # BINARY OPERATIONS
        # =================================================

        elif isinstance(node, ast.BinOp):

            left_type = None
            right_type = None

            left_value = None
            right_value = None

            # -------------------------------------------------
            # LEFT OPERAND
            # -------------------------------------------------

            if isinstance(
                node.left,
                ast.Name
            ):

                left_type = variable_types.get(
                    node.left.id
                )

                left_value = variable_values.get(
                    node.left.id
                )

            else:

                left_type = infer_type(
                    node.left
                )

                if isinstance(
                    node.left,
                    ast.Constant
                ):
                    left_value = node.left.value

            # -------------------------------------------------
            # RIGHT OPERAND
            # -------------------------------------------------

            if isinstance(
                node.right,
                ast.Name
            ):

                right_type = variable_types.get(
                    node.right.id
                )

                right_value = variable_values.get(
                    node.right.id
                )

            else:

                right_type = infer_type(
                    node.right
                )

                if isinstance(
                    node.right,
                    ast.Constant
                ):
                    right_value = node.right.value

            # =================================================
            # ZERODIVISIONERROR
            # =================================================

            if isinstance(
                node.op,
                (
                    ast.Div,
                    ast.FloorDiv,
                    ast.Mod
                )
            ):

                if right_value == 0:

                    predictions.append({
                        "type": "ZeroDivisionError",
                        "line": node.lineno,
                        "message": (
                            "The operation uses zero "
                            "as the divisor."
                        )
                    })

            # =================================================
            # TYPEERROR
            # =================================================

            if isinstance(
                node.op,
                ast.Add
            ):

                incompatible = False

                if (
                    left_type == "str"
                    and right_type in (
                        "int",
                        "float",
                        "bool"
                    )
                ):

                    incompatible = True

                elif (
                    right_type == "str"
                    and left_type in (
                        "int",
                        "float",
                        "bool"
                    )
                ):

                    incompatible = True

                if incompatible:

                    predictions.append({
                        "type": "TypeError",
                        "line": node.lineno,
                        "message": (
                            "The addition operation combines "
                            "incompatible data types."
                        )
                    })

        # =================================================
        # INDEX ERROR
        # =================================================

        elif isinstance(
            node,
            ast.Subscript
        ):

            if (
                isinstance(
                    node.slice,
                    ast.Constant
                )
                and isinstance(
                    node.slice.value,
                    int
                )
            ):

                index = node.slice.value

                predictions.append({
                    "type": "IndexError",
                    "line": node.lineno,
                    "message": (
                        f"Index {index} may be outside "
                        "the available collection range."
                    )
                })

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    unique_predictions = []

    seen = set()

    for prediction in predictions:

        key = (
            prediction["type"],
            prediction["line"],
            prediction["message"]
        )

        if key not in seen:

            seen.add(key)

            unique_predictions.append(
                prediction
            )

    return {
        "success": True,
        "predictions": unique_predictions
    }