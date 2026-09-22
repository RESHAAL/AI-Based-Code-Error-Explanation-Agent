from fastapi import FastAPI
from pydantic import BaseModel

from backend.analyzers.syntax_analyzer import analyze_syntax
from backend.analyzers.runtime_analyzer import analyze_runtime
from backend.analyzers.code_context import analyze_code_context
from backend.analyzers.root_cause_analyzer import analyze_root_cause
from backend.analyzers.error_predictor import predict_errors
from backend.analyzers.multilang_runtime_analyzer import (
    analyze_multilanguage_runtime,
    SUPPORTED_LANGUAGES
)
from backend.agents.gemini_agent import explain_error


app = FastAPI(
    title="BugLens",
    description="AI-Based Multi-Language Code Error Explanation Agent",
    version="1.0.0"
)


class CodeRequest(BaseModel):
    code: str
    language: str = "python"


@app.get("/")
def home():

    return {
        "project": "BugLens",
        "status": "running",
        "supported_languages": [
            "Python",
            "C",
            "C++",
            "Java"
        ]
    }


@app.get("/languages")
def supported_languages():

    return {
        "supported_languages": [
            "Python",
            "C",
            "C++",
            "Java"
        ]
    }


@app.post("/analyze")
def analyze_code(request: CodeRequest):

    language = request.language.strip().lower()

    # =====================================================
    # VALIDATE LANGUAGE
    # =====================================================

    if language not in SUPPORTED_LANGUAGES:

        return {
            "language": request.language,
            "analysis": {
                "has_error": True,
                "error_type": "LanguageError",
                "message": (
                    "Unsupported language. "
                    "BugLens supports Python, C, C++, and Java."
                ),
                "line": None,
                "output": ""
            },
            "prediction": {
                "success": False,
                "predictions": []
            },
            "context": {
                "success": False,
                "functions": [],
                "variables": [],
                "imports": []
            },
            "root_cause": {
                "root_cause": "Unsupported language",
                "explanation": (
                    "Please select Python, C, C++, or Java."
                ),
                "error_line": None,
                "evidence": [],
                "confidence": 1.0
            },
            "ai_explanation": None
        }

    # =====================================================
    # EMPTY CODE
    # =====================================================

    if not request.code.strip():

        return {
            "language": request.language,
            "analysis": {
                "has_error": True,
                "error_type": "InputError",
                "message": "Please enter source code.",
                "line": None,
                "output": ""
            },
            "prediction": {
                "success": False,
                "predictions": []
            },
            "context": {
                "success": False,
                "functions": [],
                "variables": [],
                "imports": []
            },
            "root_cause": {
                "root_cause": "No source code",
                "explanation": (
                    "Enter source code before running analysis."
                ),
                "error_line": None,
                "evidence": [],
                "confidence": 1.0
            },
            "ai_explanation": None
        }

    # =====================================================
    # PYTHON PIPELINE
    # =====================================================

    if language == "python":

        prediction_result = predict_errors(
            request.code
        )

        syntax_result = analyze_syntax(
            request.code
        )

        if syntax_result["has_error"]:

            return {
                "language": request.language,
                "analysis": syntax_result,
                "prediction": prediction_result,
                "context": {
                    "success": False,
                    "functions": [],
                    "variables": [],
                    "imports": []
                },
                "root_cause": {
                    "root_cause": "Syntax error",
                    "explanation": syntax_result["message"],
                    "error_line": syntax_result.get("line"),
                    "evidence": [],
                    "confidence": 0.95
                },
                "ai_explanation": None
            }

        context_result = analyze_code_context(
            request.code
        )

        runtime_result = analyze_multilanguage_runtime(
            code=request.code,
            language="python"
        )

        root_cause_result = analyze_root_cause(
            code=request.code,
            error_type=runtime_result.get(
                "error_type"
            ),
            error_message=runtime_result.get(
                "message"
            ),
            error_line=runtime_result.get(
                "line"
            ),
            context=context_result
        )

        ai_explanation = None

        if runtime_result.get("has_error"):

            try:

                ai_explanation = explain_error(
                    code=request.code,
                    error_type=runtime_result.get(
                        "error_type"
                    ),
                    error_message=runtime_result.get(
                        "message"
                    ),
                    error_line=runtime_result.get(
                        "line"
                    ),
                    context=context_result
                )

            except Exception as exc:

                ai_explanation = (
                    "Gemini analysis could not be completed. "
                    f"Reason: {str(exc)}"
                )

        return {
            "language": request.language,
            "analysis": runtime_result,
            "prediction": prediction_result,
            "context": context_result,
            "root_cause": root_cause_result,
            "ai_explanation": ai_explanation
        }

    # =====================================================
    # C / C++ / JAVA PIPELINE
    # =====================================================

    runtime_result = analyze_multilanguage_runtime(
        code=request.code,
        language=language
    )

    # These languages currently use the common execution
    # engine. Python-specific AST prediction/context
    # analysis is intentionally not applied here.

    context_result = {
        "success": False,
        "functions": [],
        "variables": [],
        "imports": []
    }

    prediction_result = {
        "success": False,
        "predictions": []
    }

    # =====================================================
    # GENERIC ROOT CAUSE
    # =====================================================

    if runtime_result.get("has_error"):

        root_cause_result = {
            "root_cause": (
                f"{runtime_result.get('error_type', 'Error')} "
                "detected"
            ),
            "explanation": runtime_result.get(
                "message",
                "The program could not execute successfully."
            ),
            "error_line": runtime_result.get(
                "line"
            ),
            "evidence": [
                runtime_result.get(
                    "message",
                    ""
                )
            ],
            "confidence": 0.75
        }

    else:

        root_cause_result = {
            "root_cause": "No runtime error",
            "explanation": (
                "The program compiled and executed successfully."
            ),
            "error_line": None,
            "evidence": [],
            "confidence": 1.0
        }

    # =====================================================
    # GEMINI EXPLANATION
    # =====================================================

    ai_explanation = None

    if runtime_result.get("has_error"):

        try:

            ai_explanation = explain_error(
                code=request.code,
                error_type=runtime_result.get(
                    "error_type"
                ),
                error_message=runtime_result.get(
                    "message"
                ),
                error_line=runtime_result.get(
                    "line"
                ),
                context={
                    "language": request.language,
                    "analysis_type": (
                        "Multi-language compiler/runtime analysis"
                    )
                }
            )

        except Exception as exc:

            ai_explanation = (
                "Gemini analysis could not be completed. "
                f"Reason: {str(exc)}"
            )

    return {
        "language": request.language,
        "analysis": runtime_result,
        "prediction": prediction_result,
        "context": context_result,
        "root_cause": root_cause_result,
        "ai_explanation": ai_explanation
    }