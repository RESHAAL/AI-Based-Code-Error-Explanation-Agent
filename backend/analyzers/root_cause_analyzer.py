def analyze_root_cause(
    code,
    error_type,
    error_message,
    error_line,
    context
):

    root_cause = "Unable to determine root cause."

    explanation = "More code context is required."

    evidence = []

    variables = context.get("variables", [])

    functions = context.get("functions", [])

    # INDEX ERROR

    if error_type == "IndexError":

        root_cause = "Invalid index access"

        explanation = (
            "The code attempted to access an index "
            "that is outside the available range "
            "of the collection."
        )

        evidence.append(
            "An indexed collection access caused the failure."
        )

    # NAME ERROR

    elif error_type == "NameError":

        root_cause = "Undefined variable or identifier"

        explanation = (
            "The code referenced a name that was "
            "not available in the current execution scope."
        )

        evidence.append(
            "The referenced identifier could not be resolved."
        )

    # TYPE ERROR

    elif error_type == "TypeError":

        root_cause = "Incompatible data type operation"

        explanation = (
            "The operation received a value of a type "
            "that it does not support."
        )

        evidence.append(
            "The operation and provided data types are incompatible."
        )

    # VALUE ERROR

    elif error_type == "ValueError":

        root_cause = "Invalid value supplied"

        explanation = (
            "The correct type of value was supplied, "
            "but the value itself is not valid for the operation."
        )

        evidence.append(
            "The operation rejected the supplied value."
        )

    # ZERO DIVISION

    elif error_type == "ZeroDivisionError":

        root_cause = "Division by zero"

        explanation = (
            "The code attempted to divide a value "
            "by zero."
        )

        evidence.append(
            "The denominator evaluated to zero."
        )

    # KEY ERROR

    elif error_type == "KeyError":

        root_cause = "Missing dictionary key"

        explanation = (
            "The requested key does not exist "
            "in the dictionary."
        )

        evidence.append(
            "The requested dictionary key was not found."
        )

    # ATTRIBUTE ERROR

    elif error_type == "AttributeError":

        root_cause = "Missing object attribute"

        explanation = (
            "The code attempted to access an attribute "
            "that does not exist on the object."
        )

        evidence.append(
            "The requested attribute was unavailable."
        )

    # GENERIC ERROR

    elif error_type:

        root_cause = f"{error_type} detected"

        explanation = (
            f"The program stopped because of a "
            f"{error_type}."
        )

        evidence.append(
            error_message
        )

    return {
        "root_cause": root_cause,
        "explanation": explanation,
        "error_line": error_line,
        "evidence": evidence,
        "confidence": 0.75,
        "related_functions": functions,
        "related_variables": variables
    }