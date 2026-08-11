def ensure_dict_output(value) -> dict:
    if not isinstance(value, dict):
        raise ValueError("LLM output must be a dict")
    return value
