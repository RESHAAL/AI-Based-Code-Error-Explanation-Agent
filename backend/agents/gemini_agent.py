import os
import re

from dotenv import load_dotenv
from google import genai
from tavily import TavilyClient


load_dotenv()


# =========================================================
# API KEYS
# =========================================================

gemini_api_key = os.getenv("GEMINI_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")


if not gemini_api_key:
    raise RuntimeError(
        "GEMINI_API_KEY was not found in the .env file."
    )


# =========================================================
# CLIENTS
# =========================================================

gemini_client = genai.Client(
    api_key=gemini_api_key
)


tavily_client = None

if tavily_api_key:
    tavily_client = TavilyClient(
        api_key=tavily_api_key
    )


MODEL_NAME = "gemini-2.5-flash"


# =========================================================
# LANGUAGE NORMALIZATION
# =========================================================

def normalize_language(language):
    if not language:
        return "Python"

    language = language.strip().lower()

    if language in ["python", "py"]:
        return "Python"

    if language == "c":
        return "C"

    if language in ["c++", "cpp"]:
        return "C++"

    return language


# =========================================================
# TAVILY WEB SEARCH
# =========================================================

def search_web_context(
    error_type,
    error_message,
    code,
    language="Python"
):
    """
    Uses Tavily to retrieve technical context related
    to the detected programming-language error.
    """

    if not tavily_client:
        return (
            "Tavily web search is not available. "
            "Continue analysis using the provided code "
            "and error information."
        )

    language = normalize_language(language)

    try:

        query = (
            f"{language} {error_type}: "
            f"{error_message} "
            f"debugging solution explanation"
        )

        response = tavily_client.search(
            query=query,
            max_results=3,
            search_depth="basic"
        )

        results = response.get(
            "results",
            []
        )

        if not results:
            return (
                "No relevant technical web documentation "
                "was found."
            )

        web_context = []

        for result in results:

            title = result.get(
                "title",
                ""
            )

            content = result.get(
                "content",
                ""
            )

            url = result.get(
                "url",
                ""
            )

            web_context.append(
                f"TITLE: {title}\n"
                f"URL: {url}\n"
                f"CONTENT: {content}"
            )

        return "\n\n".join(
            web_context
        )

    except Exception as e:

        return (
            "Tavily search failed. "
            f"Reason: {str(e)}"
        )


# =========================================================
# GEMINI ERROR EXPLANATION
# =========================================================

def explain_error(
    code,
    error_type,
    error_message,
    error_line,
    context,
    language="Python"
):

    language = normalize_language(
        language
    )

    # -----------------------------------------------------
    # Retrieve external technical context
    # -----------------------------------------------------

    web_context = search_web_context(
        error_type=error_type,
        error_message=error_message,
        code=code,
        language=language
    )

    # -----------------------------------------------------
    # Gemini prompt
    # -----------------------------------------------------

    prompt = f"""
You are BugLens, an AI-based code debugging agent.

Analyze the following {language} program and its execution
or compilation error.

PROGRAMMING LANGUAGE:
{language}

SOURCE CODE:
{code}

ERROR TYPE:
{error_type}

ERROR MESSAGE:
{error_message}

ERROR LINE:
{error_line}

CODE CONTEXT:
{context}

EXTERNAL TECHNICAL CONTEXT FROM TAVILY:
{web_context}

Use the external technical context only when it is relevant.
Do not blindly trust external information.

Give the response in this exact structure:

1. ROOT CAUSE
Explain the exact reason for the error.

2. WHY IT HAPPENED
Explain the problem in simple terms.

3. EVIDENCE
Give specific evidence from the provided code and error.

4. SUGGESTED FIX
Explain exactly what should be changed.

5. CORRECTED CODE
If a reliable correction can be determined, provide the
complete corrected {language} program inside a single code
block.

Rules:
- Do not invent variables or requirements.
- Use only information supported by the code, error,
  and relevant technical context.
- Keep the explanation concise and easy to understand.
- Do not claim that the code is fixed unless the correction
  is supported by the provided evidence.
"""

    response = gemini_client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


# =========================================================
# EXTRACT CORRECTED CODE
# =========================================================

def extract_corrected_code(
    ai_result
):

    if not ai_result:
        return None

    # Python
    python_match = re.search(
        r"```python\s*(.*?)```",
        ai_result,
        re.DOTALL | re.IGNORECASE
    )

    if python_match:

        code = python_match.group(
            1
        ).strip()

        if code:
            return code

    # C++
    cpp_match = re.search(
        r"```(?:cpp|c\+\+)\s*(.*?)```",
        ai_result,
        re.DOTALL | re.IGNORECASE
    )

    if cpp_match:

        code = cpp_match.group(
            1
        ).strip()

        if code:
            return code

    # C
    c_match = re.search(
        r"```c\s*(.*?)```",
        ai_result,
        re.DOTALL | re.IGNORECASE
    )

    if c_match:

        code = c_match.group(
            1
        ).strip()

        if code:
            return code

    # Generic code block
    generic_match = re.search(
        r"```\s*(.*?)```",
        ai_result,
        re.DOTALL
    )

    if generic_match:

        code = generic_match.group(
            1
        ).strip()

        if code:
            return code

    return None


# =========================================================
# SECOND REPAIR / RETRY
# =========================================================

def retry_repair(
    failed_code,
    error_type,
    error_message,
    error_line,
    previous_attempt,
    context,
    language="Python"
):

    language = normalize_language(
        language
    )

    # -----------------------------------------------------
    # Retrieve additional technical context
    # -----------------------------------------------------

    web_context = search_web_context(
        error_type=error_type,
        error_message=error_message,
        code=failed_code,
        language=language
    )

    prompt = f"""
You are BugLens, an autonomous debugging and repair agent.

The first generated repair FAILED verification.

You must analyze the failed repair and generate a new
corrected version.

PROGRAMMING LANGUAGE:
{language}

ORIGINAL / FAILED REPAIRED CODE:
{failed_code}

ERROR TYPE:
{error_type}

ERROR MESSAGE:
{error_message}

ERROR LINE:
{error_line}

PREVIOUS AI REPAIR:
{previous_attempt}

CODE CONTEXT:
{context}

EXTERNAL TECHNICAL CONTEXT FROM TAVILY:
{web_context}

Perform a second debugging attempt.

Return exactly:

1. ROOT CAUSE OF REMAINING ERROR
Explain why the previous repair still failed.

2. NEW FIX
Explain what must be changed.

3. CORRECTED CODE
Provide the COMPLETE corrected {language} program
inside exactly one code block.

Rules:
- Do not repeat a failed fix.
- The new code must be executable {language}.
- Preserve the original program's intended purpose.
- Do not invent external files or dependencies.
- Use only information supported by the code, error,
  and relevant technical context.
"""

    response = gemini_client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text


# =========================================================
# GENERATE SECOND REPAIR
# =========================================================

def generate_second_repair(
    failed_code,
    error_type,
    error_message,
    error_line,
    previous_attempt,
    context,
    language="Python"
):

    result = retry_repair(
        failed_code=failed_code,
        error_type=error_type,
        error_message=error_message,
        error_line=error_line,
        previous_attempt=previous_attempt,
        context=context,
        language=language
    )

    corrected_code = extract_corrected_code(
        result
    )

    return {
        "explanation": result,
        "corrected_code": corrected_code
    }