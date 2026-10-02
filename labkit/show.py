"""Print the parts of a SystemOneResponse that the lessons talk about."""
from __future__ import annotations


def tokens(usage) -> str:
    def fmt(v):
        return "not reported" if v is None else str(v)
    return f"input_tokens={fmt(usage.input_tokens)} output_tokens={fmt(usage.output_tokens)}"


def request_id(response) -> str:
    """The SDK raises if the response had no request-ID header; show that as 'not reported'."""
    from typesafe_sdk import TypeSafeError

    try:
        return response.request_id
    except TypeSafeError:
        return "not reported"


def response_footer(response) -> str:
    return f"model={response.model}  {tokens(response.usage)}  request_id={request_id(response)}"
