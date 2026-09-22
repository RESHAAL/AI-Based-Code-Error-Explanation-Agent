import time
import gradio as gr

from backend.analyzers.syntax_analyzer import analyze_syntax
from backend.analyzers.code_context import analyze_code_context
from backend.analyzers.root_cause_analyzer import analyze_root_cause
from backend.analyzers.error_predictor import predict_errors
from backend.analyzers.multilang_runtime_analyzer import (
    analyze_multilanguage_runtime
)

from backend.agents.gemini_agent import (
    explain_error,
    extract_corrected_code,
    generate_second_repair
)


# ============================================================
# LANGUAGE HELPERS
# ============================================================

LANGUAGE_MAP = {
    "Python": "python",
    "C": "c",
    "C++": "cpp"
}


def get_language_name(language):
    return LANGUAGE_MAP.get(
        language,
        "python"
    )


def get_editor_language(language):
    return LANGUAGE_MAP.get(
        language,
        "python"
    )


def update_editor_language(language):
    return gr.update(
        language=get_editor_language(language),
        value=""
    )


# ============================================================
# STATUS
# ============================================================

def make_status(
    title,
    message,
    kind="loading"
):

    if kind == "success":
        icon = "✅"

    elif kind == "error":
        icon = "❌"

    else:
        icon = "🔄"

    return (
        '<div class="status-card status-' + kind + '">'
        '<div class="status-icon">' + icon + '</div>'
        '<div>'
        '<div class="status-title">' + title + '</div>'
        '<div class="status-message">' + message + '</div>'
        '</div>'
        '</div>'
    )


# ============================================================
# CODE CONTEXT
# ============================================================

def context_markdown(context):

    functions = context.get(
        "functions",
        []
    )

    variables = context.get(
        "variables",
        []
    )

    imports = context.get(
        "imports",
        []
    )

    function_text = "\n".join(
        "- `" + str(item["name"]) +
        "` — line " + str(item["line"])
        for item in functions
    )

    variable_text = "\n".join(
        "- `" + str(item["name"]) +
        "` — line " + str(item["line"])
        for item in variables
    )

    import_text = "\n".join(
        "- `" + str(item) + "`"
        for item in imports
    )

    if not function_text:
        function_text = "- No functions detected."

    if not variable_text:
        variable_text = "- No variables detected."

    if not import_text:
        import_text = "- No imports detected."

    return (
        "## 🧩 Code Context\n\n"
        "### Functions\n"
        + function_text
        + "\n\n### Variables\n"
        + variable_text
        + "\n\n### Imports\n"
        + import_text
    )


# ============================================================
# ERROR PREDICTION
# ============================================================

def prediction_markdown(prediction):

    if not prediction:
        return (
            "## 🔮 Error Prediction\n\n"
            "No prediction data available."
        )

    predictions = prediction.get(
        "predictions",
        []
    )

    if not prediction.get(
        "success",
        False
    ) and not predictions:

        return (
            "## 🔮 Error Prediction\n\n"
            "Static prediction could not be completed."
        )

    if not predictions:
        return (
            "## 🔮 Error Prediction\n\n"
            "### ✅ No obvious runtime risk detected\n\n"
            "Static analysis did not identify a common "
            "runtime error pattern before execution."
        )

    prediction_rows = []

    for item in predictions:

        error_type = item.get(
            "type",
            "Unknown"
        )

        line = item.get(
            "line",
            "Unknown"
        )

        message = item.get(
            "message",
            ""
        )

        prediction_rows.append(
            "| `"
            + str(error_type)
            + "` | `"
            + str(line)
            + "` | "
            + str(message)
            + " |"
        )

    return (
        "## 🔮 Error Prediction\n\n"
        "**Static analysis detected the following possible "
        "runtime risks before execution:**\n\n"
        "| Possible Error | Line | Prediction |\n"
        "|---|---|---|\n"
        + "\n".join(prediction_rows)
        + "\n\n"
        "_Predictions are currently based on Python static "
        "analysis and are verified through actual execution._"
    )


# ============================================================
# NON-PYTHON PREDICTION
# ============================================================

def non_python_prediction(language):

    return (
        "## 🔮 Error Prediction\n\n"
        "Static AST prediction is currently enabled for "
        "**Python**.\n\n"
        "**Selected Language:** `"
        + str(language)
        + "`\n\n"
        "For this language, BugLens performs compiler/runtime "
        "analysis and verifies the actual execution result."
    )


# ============================================================
# ERROR OUTPUT
# ============================================================

def error_markdown(runtime):

    error_type = runtime.get(
        "error_type",
        "RuntimeError"
    )

    message = runtime.get(
        "message",
        ""
    )

    line = runtime.get(
        "line",
        "Unknown"
    )

    output = runtime.get(
        "output",
        ""
    )

    if not output:
        output = "No output produced before failure."

    return (
        "## 🚨 Error Detected\n\n"
        "| Property | Details |\n"
        "|---|---|\n"
        "| Error Type | `"
        + str(error_type)
        + "` |\n"
        "| Message | "
        + str(message)
        + " |\n"
        "| Error Line | `"
        + str(line)
        + "` |\n\n"
        "### Program Output\n\n"
        "```text\n"
        + str(output)
        + "\n```"
    )


# ============================================================
# SUCCESS OUTPUT
# ============================================================

def success_markdown(
    runtime,
    language
):

    output = runtime.get(
        "output",
        ""
    )

    if not output:
        output = "No output produced."

    return (
        "## ✅ Code Executed Successfully\n\n"
        "**Language:** `"
        + str(language)
        + "`\n\n"
        "**Status:** No runtime error detected.\n\n"
        "### Program Output\n\n"
        "```text\n"
        + str(output)
        + "\n```"
    )


# ============================================================
# ROOT CAUSE
# ============================================================

def root_markdown(root):

    evidence = root.get(
        "evidence",
        []
    )

    evidence_text = "\n".join(
        "- " + str(item)
        for item in evidence
    )

    if not evidence_text:
        evidence_text = "- No additional evidence available."

    confidence = (
        float(
            root.get(
                "confidence",
                0
            )
        ) * 100
    )

    return (
        "## 🎯 Root Cause\n\n"
        "### "
        + str(
            root.get(
                "root_cause",
                "Unknown"
            )
        )
        + "\n\n"
        + str(
            root.get(
                "explanation",
                ""
            )
        )
        + "\n\n"
        "### Evidence\n\n"
        + evidence_text
        + "\n\n"
        "**Confidence:** "
        + str(round(confidence))
        + "%"
    )


# ============================================================
# REPAIR VERIFICATION
# ============================================================

def verify_python_repair(code):

    """
    Uses the same multi-language execution engine used by
    the main BugLens pipeline.

    This keeps original execution and repair verification
    consistent.
    """

    return analyze_multilanguage_runtime(
        code=code,
        language="python"
    )


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_bug(
    code,
    selected_language
):

    language = get_language_name(
        selected_language
    )

    # ========================================================
    # EMPTY CODE
    # ========================================================

    if not code or not code.strip():

        yield (
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            make_status(
                "Ready",
                "Enter code and click Analyze Code.",
                "success"
            )
        )

        return

    # ========================================================
    # STEP 1
    # ========================================================

    yield (
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        make_status(
            "Analysis started",
            f"Preparing {selected_language} code...",
            "loading"
        )
    )

    time.sleep(0.2)

    # ========================================================
    # PYTHON SYNTAX CHECK
    # ========================================================

    if language == "python":

        yield (
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            make_status(
                "Checking syntax",
                "Analyzing Python syntax...",
                "loading"
            )
        )

        syntax = analyze_syntax(
            code
        )

        if syntax.get(
            "has_error"
        ):

            prediction = predict_errors(
                code
            )

            analysis = (
                "## ⚠️ Syntax Error\n\n"
                "| Property | Details |\n"
                "|---|---|\n"
                "| Error Type | `"
                + str(
                    syntax.get(
                        "error_type",
                        "SyntaxError"
                    )
                )
                + "` |\n"
                "| Message | "
                + str(
                    syntax.get(
                        "message",
                        ""
                    )
                )
                + " |\n"
                "| Line | `"
                + str(
                    syntax.get(
                        "line",
                        "Unknown"
                    )
                )
                + "` |"
            )

            prediction_text = prediction_markdown(
                prediction
            )

            yield (
                analysis,
                "",
                prediction_text,
                "",
                "",
                "",
                "## 🔧 Repair Verification\n\n"
                "Fix the syntax error first.",
                make_status(
                    "Syntax error detected",
                    "Please correct the syntax and analyze again.",
                    "error"
                )
            )

            return

    # ========================================================
    # CODE CONTEXT
    # ========================================================

    yield (
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        make_status(
            "Reading code context",
            "Analyzing the source code...",
            "loading"
        )
    )

    if language == "python":

        context = analyze_code_context(
            code
        )

        context_text = context_markdown(
            context
        )

    else:

        context = {
            "success": False,
            "functions": [],
            "variables": [],
            "imports": []
        }

        context_text = (
            "## 🧩 Code Context\n\n"
            f"**Language:** `{selected_language}`\n\n"
            "Language-specific source context extraction "
            "is not enabled yet. Compiler/runtime analysis "
            "is active."
        )

    # ========================================================
    # ERROR PREDICTION
    # ========================================================

    if language == "python":

        yield (
            "",
            context_text,
            "",
            "",
            "",
            "",
            "",
            make_status(
                "Predicting possible errors",
                "Scanning Python code for risky patterns...",
                "loading"
            )
        )

        prediction = predict_errors(
            code
        )

        prediction_text = prediction_markdown(
            prediction
        )

    else:

        prediction = {
            "success": False,
            "predictions": []
        }

        prediction_text = non_python_prediction(
            selected_language
        )

    # ========================================================
    # EXECUTION
    # ========================================================

    yield (
        "",
        context_text,
        prediction_text,
        "",
        "",
        "",
        "",
        make_status(
            "Running your program",
            f"Compiling/executing {selected_language} code...",
            "loading"
        )
    )

    runtime = analyze_multilanguage_runtime(
        code=code,
        language=language
    )

    # ========================================================
    # SUCCESS
    # ========================================================

    if not runtime.get(
        "has_error"
    ):

        yield (
            success_markdown(
                runtime,
                selected_language
            ),
            context_text,
            prediction_text,
            "## 🎯 Root Cause\n\n"
            "No root cause required because the program "
            "executed successfully.",
            "## 🤖 BugLens AI\n\n"
            "No AI repair was required.",
            "## 🔍 Verification\n\n"
            "**Status:** `PASSED`\n\n"
            f"The {selected_language} program compiled "
            "and executed successfully.",
            "## 🔧 Repair Verification\n\n"
            "No repair was required.",
            make_status(
                "Analysis complete",
                f"{selected_language} code executed successfully.",
                "success"
            )
        )

        return

    # ========================================================
    # ROOT CAUSE
    # ========================================================

    yield (
        "",
        context_text,
        prediction_text,
        "",
        "",
        "",
        "",
        make_status(
            "Finding root cause",
            "Connecting the execution error with the code...",
            "loading"
        )
    )

    if language == "python":

        root = analyze_root_cause(
            code=code,
            error_type=runtime.get(
                "error_type"
            ),
            error_message=runtime.get(
                "message"
            ),
            error_line=runtime.get(
                "line"
            ),
            context=context
        )

    else:

        root = {
            "root_cause": (
                f"{runtime.get('error_type', 'Error')} detected"
            ),
            "explanation": runtime.get(
                "message",
                "The program could not execute successfully."
            ),
            "error_line": runtime.get(
                "line"
            ),
            "evidence": [
                runtime.get(
                    "message",
                    ""
                )
            ],
            "confidence": 0.75
        }

    analysis = error_markdown(
        runtime
    )

    root_text = root_markdown(
        root
    )

    # ========================================================
    # GEMINI
    # ========================================================

    yield (
        analysis,
        context_text,
        prediction_text,
        root_text,
        "",
        "",
        "",
        make_status(
            "Gemini is analyzing",
            "Generating explanation and possible correction...",
            "loading"
        )
    )

    try:

        ai_result = explain_error(
            code=code,
            error_type=runtime.get(
                "error_type"
            ),
            error_message=runtime.get(
                "message"
            ),
            error_line=runtime.get(
                "line"
            ),
            context={
                **context,
                "language": selected_language
            },
            language=selected_language
        )

    except Exception as exc:

        ai_result = (
            "Gemini analysis failed.\n\n"
            "Reason: "
            + str(exc)
        )

    ai_text = (
        "## 🤖 BugLens AI Explanation\n\n"
        + str(ai_result)
    )

    # ========================================================
    # NON-PYTHON REPAIR NOTICE
    # ========================================================

    if language != "python":

        yield (
            analysis,
            context_text,
            prediction_text,
            root_text,
            ai_text,
            (
                "## 🔍 Verification\n\n"
                "**Original Status:** `ERROR`\n\n"
                f"The {selected_language} program "
                "was compiled/executed and the error "
                "was reproduced."
            ),
            (
                "## 🔧 Repair Verification\n\n"
                "### ℹ️ Multi-Language Analysis\n\n"
                f"BugLens successfully analyzed the "
                f"{selected_language} program.\n\n"
                "Automatic repair extraction and iterative "
                "repair verification are currently enabled "
                "for Python."
            ),
            make_status(
                "Analysis complete",
                f"{selected_language} error detected and analyzed.",
                "success"
            )
        )

        return

    # ========================================================
    # PYTHON REPAIR
    # ========================================================

    yield (
        analysis,
        context_text,
        prediction_text,
        root_text,
        ai_text,
        "",
        "",
        make_status(
            "Generating repair",
            "Creating corrected Python code...",
            "loading"
        )
    )

    corrected_code = extract_corrected_code(
        ai_result
    )

    if not corrected_code:

        yield (
            analysis,
            context_text,
            prediction_text,
            root_text,
            ai_text,
            "## 🔍 Verification\n\n"
            "**Original Status:** `ERROR`\n\n"
            "The original error was reproduced.",
            "## 🔧 Repair Verification\n\n"
            "### ⚠️ Repair Unavailable\n\n"
            "A complete corrected program could not be extracted.",
            make_status(
                "Analysis complete",
                "Error found, but automatic repair was unavailable.",
                "error"
            )
        )

        return

    # ========================================================
    # VERIFY FIRST REPAIR
    # ========================================================

    yield (
        analysis,
        context_text,
        prediction_text,
        root_text,
        ai_text,
        "",
        (
            "## 🔧 Repair Verification\n\n"
            "### 🔄 Repair Attempt 1\n\n"
            "Running the generated correction using "
            "the BugLens execution engine..."
        ),
        make_status(
            "Verifying repair",
            "Running the first generated fix...",
            "loading"
        )
    )

    repaired = verify_python_repair(
        corrected_code
    )

    # ========================================================
    # FIRST REPAIR PASSED
    # ========================================================

    if not repaired.get(
        "has_error"
    ):

        repaired_output = repaired.get(
            "output",
            ""
        )

        if not repaired_output:
            repaired_output = "No output produced."

        verification = (
            "## 🔍 Verification\n\n"
            "**Original Status:** `ERROR`\n\n"
            "**Repair Attempt 1:** `PASSED`\n\n"
            "**Final Verification:** `PASSED`\n\n"
            "The original bug was reproduced and "
            "the generated repair executed successfully."
        )

        repair = (
            "## 🔧 Repair Verification\n\n"
            "### ✅ Repair Successful\n\n"
            "**Repair Attempt:** `1`\n\n"
            "**Verification Status:** `PASSED`\n\n"
            "### Corrected Code\n\n"
            "```python\n"
            + corrected_code
            + "\n```\n\n"
            "### Corrected Program Output\n\n"
            "```text\n"
            + str(repaired_output)
            + "\n```"
        )

        yield (
            analysis,
            context_text,
            prediction_text,
            root_text,
            ai_text,
            verification,
            repair,
            make_status(
                "Analysis complete",
                "Bug detected → prediction → explanation → repair → verification PASSED.",
                "success"
            )
        )

        return

    # ========================================================
    # FIRST REPAIR FAILED
    # ========================================================

    first_failure_type = repaired.get(
        "error_type",
        "RuntimeError"
    )

    first_failure_message = repaired.get(
        "message",
        ""
    )

    first_failure_line = repaired.get(
        "line",
        "Unknown"
    )

    yield (
        analysis,
        context_text,
        prediction_text,
        root_text,
        ai_text,
        "",
        (
            "## 🔧 Repair Verification\n\n"
            "### ⚠️ First Repair Failed\n\n"
            "**Repair Attempt:** `1`\n\n"
            "**Error:** `"
            + str(first_failure_type)
            + "`\n\n"
            "**Message:** "
            + str(first_failure_message)
            + "\n\n"
            "BugLens is automatically re-analyzing the failed repair."
        ),
        make_status(
            "Repair failed — retrying",
            "First fix failed verification. Starting repair attempt 2...",
            "loading"
        )
    )

    # ========================================================
    # SECOND REPAIR
    # ========================================================

    yield (
        analysis,
        context_text,
        prediction_text,
        root_text,
        ai_text,
        "",
        (
            "## 🔧 Repair Verification\n\n"
            "### 🔄 Repair Attempt 2\n\n"
            "BugLens is sending the failed repair back "
            "to the AI agent for re-analysis..."
        ),
        make_status(
            "Re-analyzing failed repair",
            "Gemini is generating a second correction...",
            "loading"
        )
    )

    try:

        second_result = generate_second_repair(
            failed_code=corrected_code,
            error_type=first_failure_type,
            error_message=first_failure_message,
            error_line=first_failure_line,
            previous_attempt=ai_result,
            context=context,
            language=selected_language
        )

        second_ai_text = second_result.get(
            "explanation",
            ""
        )

        second_corrected_code = second_result.get(
            "corrected_code"
        )

    except Exception as exc:

        second_ai_text = (
            "Second repair attempt failed.\n\n"
            "Reason: "
            + str(exc)
        )

        second_corrected_code = None

    # ========================================================
    # SECOND REPAIR EXTRACTION FAILED
    # ========================================================

    if not second_corrected_code:

        verification = (
            "## 🔍 Verification\n\n"
            "**Original Status:** `ERROR`\n\n"
            "**Repair Attempt 1:** `FAILED`\n\n"
            "**Repair Attempt 2:** `FAILED`\n\n"
            "A second corrected program could not be generated."
        )

        repair = (
            "## 🔧 Repair Verification\n\n"
            "### ❌ Automatic Repair Failed\n\n"
            "BugLens attempted two repair iterations.\n\n"
            "**Attempt 1:** Failed verification\n\n"
            "**Attempt 2:** No valid corrected code generated.\n\n"
            "### Second Agent Analysis\n\n"
            + str(second_ai_text)
        )

        yield (
            analysis,
            context_text,
            prediction_text,
            root_text,
            ai_text,
            verification,
            repair,
            make_status(
                "Repair unsuccessful",
                "Two repair attempts were completed without a verified fix.",
                "error"
            )
        )

        return

    # ========================================================
    # VERIFY SECOND REPAIR
    # ========================================================

    yield (
        analysis,
        context_text,
        prediction_text,
        root_text,
        ai_text,
        "",
        (
            "## 🔧 Repair Verification\n\n"
            "### 🔄 Verifying Repair Attempt 2\n\n"
            "Executing the second generated correction..."
        ),
        make_status(
            "Verifying second repair",
            "Running repair attempt 2...",
            "loading"
        )
    )

    second_repaired = verify_python_repair(
        second_corrected_code
    )

    # ========================================================
    # SECOND REPAIR PASSED
    # ========================================================

    if not second_repaired.get(
        "has_error"
    ):

        second_output = second_repaired.get(
            "output",
            ""
        )

        if not second_output:
            second_output = "No output produced."

        verification = (
            "## 🔍 Verification\n\n"
            "**Original Status:** `ERROR`\n\n"
            "**Repair Attempt 1:** `FAILED`\n\n"
            "**Repair Attempt 2:** `PASSED`\n\n"
            "**Final Verification:** `PASSED`\n\n"
            "BugLens re-analyzed the failed repair, generated "
            "a second correction, and successfully verified it."
        )

        repair = (
            "## 🔧 Repair Verification\n\n"
            "### ✅ Repair Successful\n\n"
            "**Repair Attempt:** `2`\n\n"
            "**Verification Status:** `PASSED`\n\n"
            "### Agentic Retry\n\n"
            "The first repair failed verification. "
            "BugLens automatically re-analyzed the failure "
            "and generated a second repair.\n\n"
            "### Corrected Code\n\n"
            "```python\n"
            + second_corrected_code
            + "\n```\n\n"
            "### Corrected Program Output\n\n"
            "```text\n"
            + str(second_output)
            + "\n```"
        )

        yield (
            analysis,
            context_text,
            prediction_text,
            root_text,
            ai_text,
            verification,
            repair,
            make_status(
                "Analysis complete",
                "Repair attempt 1 failed → AI re-analysis → repair attempt 2 PASSED.",
                "success"
            )
        )

        return

    # ========================================================
    # SECOND REPAIR FAILED
    # ========================================================

    second_error_type = second_repaired.get(
        "error_type",
        "RuntimeError"
    )

    second_error_message = second_repaired.get(
        "message",
        ""
    )

    verification = (
        "## 🔍 Verification\n\n"
        "**Original Status:** `ERROR`\n\n"
        "**Repair Attempt 1:** `FAILED`\n\n"
        "**Repair Attempt 2:** `FAILED`\n\n"
        "**Final Verification:** `FAILED`"
    )

    repair = (
        "## 🔧 Repair Verification\n\n"
        "### ❌ Repair Verification Failed\n\n"
        "BugLens completed two autonomous repair attempts.\n\n"
        "| Attempt | Result |\n"
        "|---|---|\n"
        "| Repair 1 | `FAILED` |\n"
        "| Repair 2 | `FAILED` |\n\n"
        "### Remaining Error\n\n"
        "**Error Type:** `"
        + str(second_error_type)
        + "`\n\n"
        "**Message:** "
        + str(second_error_message)
        + "\n\n"
        "### Second Generated Code\n\n"
        "```python\n"
        + second_corrected_code
        + "\n```"
    )

    yield (
        analysis,
        context_text,
        prediction_text,
        root_text,
        ai_text,
        verification,
        repair,
        make_status(
            "Repair unsuccessful",
            "Two autonomous repair attempts were completed but verification failed.",
            "error"
        )
    )


# ============================================================
# CSS
# ============================================================

custom_css = """

html,
body {
    margin: 0 !important;
    padding: 0 !important;
    background: #f7f1e8 !important;
}

body {
    font-family: Arial, Helvetica, sans-serif !important;
}

.gradio-container {
    width: 100% !important;
    max-width: none !important;
    min-height: 100vh !important;
    margin: 0 !important;
    padding: 0 30px 30px 30px !important;
    background: #f7f1e8 !important;
    color: #2f2925 !important;
}

.title-box {
    width: 100%;
    text-align: center;
    padding: 24px 0 20px 0;
}

.title-box h1 {
    margin: 0;
    font-size: 46px;
    font-weight: 800;
    color: #c94c4c !important;
}

.title-box p {
    margin: 7px 0 0 0;
    color: #675950 !important;
    font-size: 17px;
}

.dashboard-row {
    width: 100% !important;
    gap: 28px !important;
    align-items: flex-start !important;
}

.section-heading,
.section-heading * {
    color: #2f2925 !important;
    font-size: 23px !important;
    font-weight: 750 !important;
}

.output-card {
    background: #fffaf3 !important;
    background-color: #fffaf3 !important;
    border: 1px solid #ead8c5 !important;
    border-radius: 14px !important;
    padding: 16px !important;
    margin-bottom: 12px !important;
    box-shadow: 0 3px 12px rgba(82, 55, 40, 0.07) !important;
}

.output-card > div,
.output-card > div > div,
.output-card .wrap,
.output-card .form,
.output-card .block,
.output-card .prose {
    background: #fffaf3 !important;
    background-color: #fffaf3 !important;
}

.output-card .prose,
.output-card .prose p,
.output-card .prose li,
.output-card .prose strong,
.output-card .prose em,
.output-card .prose h1,
.output-card .prose h2,
.output-card .prose h3,
.output-card .prose h4,
.output-card .prose h5,
.output-card .prose h6,
.output-card .prose span,
.output-card .prose label,
.output-card .prose td,
.output-card .prose th {
    color: #2f2925 !important;
}

.output-card .prose code {
    background: #ead8c5 !important;
    background-color: #ead8c5 !important;
    color: #4e332d !important;
    border: 1px solid #d8bfa7 !important;
    border-radius: 4px !important;
    padding: 2px 6px !important;
    font-size: 0.92em !important;
    font-weight: 600 !important;
}

.output-card .prose pre {
    background: #29292d !important;
    background-color: #29292d !important;
    color: #ffffff !important;
    border-radius: 9px !important;
    padding: 15px !important;
    overflow-x: auto !important;
    border: none !important;
}

.output-card .prose pre,
.output-card .prose pre code,
.output-card .prose pre span,
.output-card .prose pre div,
.output-card .prose pre p,
.output-card .prose pre strong,
.output-card .prose pre em,
.output-card .prose pre b,
.output-card .prose pre i,
.output-card .prose pre * {
    background: transparent !important;
    background-color: transparent !important;
    color: #ffffff !important;
    border-color: transparent !important;
    text-shadow: none !important;
}

.output-card .prose pre {
    background: #29292d !important;
}

.output-card .prose pre code {
    border: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
    font-weight: normal !important;
}

.output-card table {
    width: 100% !important;
    border-collapse: collapse !important;
    background: #fffaf3 !important;
}

.output-card thead,
.output-card tbody,
.output-card tr {
    background: #fffaf3 !important;
}

.output-card th {
    background: #ead8c5 !important;
    color: #4e332d !important;
    border: 1px solid #ddc9b5 !important;
    padding: 9px !important;
}

.output-card td {
    background: #fffaf3 !important;
    color: #2f2925 !important;
    border: 1px solid #ddc9b5 !important;
    padding: 9px !important;
}

.gradio-code {
    background: #29292d !important;
    color: white !important;
    border-radius: 10px !important;
}

.gradio-code .cm-editor,
.gradio-code .cm-scroller {
    background: #29292d !important;
}

.gradio-code .cm-content,
.gradio-code .cm-line,
.gradio-code .cm-line span,
.gradio-code .cm-content span {
    color: white !important;
}

.gradio-code .cm-gutters {
    background: #29292d !important;
    color: white !important;
    border-right: 1px solid #444 !important;
}

.gradio-code .cm-gutterElement {
    color: white !important;
}

.gradio-code .cm-cursor {
    border-left-color: white !important;
}

.gradio-code label,
.gradio-code label span {
    color: white !important;
}

.gradio-code button {
    background: #202024 !important;
    color: white !important;
}

.gradio-code button svg,
.gradio-code button svg path,
.gradio-code button svg line,
.gradio-code button svg polyline {
    color: white !important;
    stroke: white !important;
}

.language-dropdown {
    margin-bottom: 8px !important;
}

.language-dropdown label,
.language-dropdown span {
    color: #2f2925 !important;
    font-weight: 700 !important;
}

.analyze-btn {
    background: #c94c4c !important;
    color: white !important;
    border: none !important;
    border-radius: 9px !important;
    min-height: 52px !important;
    font-size: 17px !important;
    font-weight: 700 !important;
    margin-top: 12px !important;
    box-shadow: 0 4px 10px rgba(201, 76, 76, 0.20) !important;
}

.analyze-btn *,
.analyze-btn span {
    color: white !important;
}

.analyze-btn:hover {
    background: #b84242 !important;
}

.clear-btn {
    background: #ead8c5 !important;
    color: #713f3f !important;
    border: 1px solid #c94c4c !important;
    border-radius: 9px !important;
    min-height: 48px !important;
    font-weight: 650 !important;
    margin-top: 8px !important;
}

.clear-btn *,
.clear-btn span {
    color: #713f3f !important;
}

.clear-btn:hover {
    background: #dfc3aa !important;
}

.status-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 13px 16px;
    margin-bottom: 18px;
    border-radius: 11px;
    background: #fffaf3 !important;
    border: 1px solid #ead8c5 !important;
}

.status-loading {
    border-left: 5px solid #c94c4c !important;
}

.status-success {
    border-left: 5px solid #4c9a65 !important;
}

.status-error {
    border-left: 5px solid #c94c4c !important;
}

.status-icon {
    font-size: 23px;
}

.status-title {
    font-weight: 750;
    color: #2f2925 !important;
}

.status-message {
    font-size: 13px;
    color: #6c5c52 !important;
    margin-top: 2px;
}

@media (max-width: 900px) {

    .gradio-container {
        padding: 0 14px 20px 14px !important;
    }

    .dashboard-row {
        flex-direction: column !important;
    }

    .title-box h1 {
        font-size: 36px;
    }
}
"""


# ============================================================
# GRADIO APP
# ============================================================

with gr.Blocks(
    title="BugLens — AI Multi-Language Code Error Explanation Agent",
    css=custom_css
) as demo:

    gr.HTML(
        """
        <div class="title-box">
            <h1>🐞 BugLens</h1>
            <p>AI-Based Multi-Language Code Error Explanation Agent</p>
            <p>Detect • Predict • Explain • Diagnose • Repair • Verify</p>
        </div>
        """
    )

    status_output = gr.HTML(
        value=make_status(
            "Ready",
            "Select a language, enter your code, and click Analyze Code.",
            "success"
        )
    )

    with gr.Row(
        elem_classes=["dashboard-row"]
    ):

        with gr.Column(
            scale=5
        ):

            gr.Markdown(
                "## 💻 Source Code",
                elem_classes=["section-heading"]
            )

            language_dropdown = gr.Dropdown(
                choices=[
                    "Python",
                    "C",
                    "C++"
                ],
                value="Python",
                label="Select Programming Language",
                elem_classes=["language-dropdown"]
            )

            code_input = gr.Code(
                label="Enter Your Code",
                language="python",
                value="",
                lines=18
            )

            analyze_button = gr.Button(
                "🔍 Analyze Code",
                variant="primary",
                elem_classes=["analyze-btn"]
            )

            clear_button = gr.Button(
                "🧹 Clear",
                elem_classes=["clear-btn"]
            )

            gr.Markdown(
                """
### 💡 BugLens Workflow

**Select Language** → **Detect** → **Predict** → **Diagnose** → **Explain** → **Repair** → **Verify**
""",
                elem_classes=["output-card"]
            )

        with gr.Column(
            scale=7
        ):

            gr.Markdown(
                "## 📊 Bug Analysis",
                elem_classes=["section-heading"]
            )

            with gr.Group(
                elem_classes=["output-card"]
            ):
                analysis_output = gr.Markdown()

            with gr.Group(
                elem_classes=["output-card"]
            ):
                context_output = gr.Markdown()

            with gr.Group(
                elem_classes=["output-card"]
            ):
                prediction_output = gr.Markdown()

            with gr.Group(
                elem_classes=["output-card"]
            ):
                root_output = gr.Markdown()

            with gr.Group(
                elem_classes=["output-card"]
            ):
                ai_output = gr.Markdown()

            with gr.Group(
                elem_classes=["output-card"]
            ):
                verification_output = gr.Markdown()

            with gr.Group(
                elem_classes=["output-card"]
            ):
                repair_output = gr.Markdown()

    # ========================================================
    # LANGUAGE CHANGE
    # ========================================================

    language_dropdown.change(
        fn=update_editor_language,
        inputs=language_dropdown,
        outputs=code_input
    )

    # ========================================================
    # ANALYZE
    # ========================================================

    analyze_button.click(
        fn=analyze_bug,
        inputs=[
            code_input,
            language_dropdown
        ],
        outputs=[
            analysis_output,
            context_output,
            prediction_output,
            root_output,
            ai_output,
            verification_output,
            repair_output,
            status_output
        ]
    )

    # ========================================================
    # CLEAR
    # ========================================================

    clear_button.click(
        fn=lambda: (
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            make_status(
                "Ready",
                "Select a language, enter your code, and click Analyze Code.",
                "success"
            )
        ),
        inputs=None,
        outputs=[
            code_input,
            analysis_output,
            context_output,
            prediction_output,
            root_output,
            ai_output,
            verification_output,
            repair_output,
            status_output
        ]
    )


# ============================================================
# START APP
# ============================================================

if __name__ == "__main__":

    demo.launch()