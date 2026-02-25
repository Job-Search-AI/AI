def generate_response(user_prompt, documents):
    from src.llm.generator import generate_response as _generate_response

    return _generate_response(user_prompt, documents)

__all__ = ["generate_response"]
