import ast


def validate_python(code):
    try:
        ast.parse(code)
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {"valid": False, "error": f"Linha {e.lineno}: {e.msg}"}


def validate_file(path, content, language):
    if language == "python" or path.endswith(".py"):
        return validate_python(content)
    return {"valid": True, "error": None}
