"""HTML completeness and retry tests."""

import asyncio

from launchkit.generation.html_generation import HtmlGenerationService, html_looks_complete


class TextStub:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.prompts: list[str] = []

    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4_000,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        del system, max_tokens, model, temperature
        self.prompts.append(prompt)
        return next(self.responses)


def complete_html(label: str, size: int = 1_200) -> str:
    return f"<!DOCTYPE html><html><body><h1>{label}</h1>{'x' * size}</body></html>"


def test_html_completeness_requires_document_headline_close_and_size() -> None:
    assert html_looks_complete(complete_html("Good")) is True
    assert html_looks_complete("<html><h1>Short</h1></html>") is False
    assert html_looks_complete("x" * 1300 + "</html>") is False
    assert html_looks_complete("<!DOCTYPE html><p>" + "x" * 1300 + "</p></html>") is False


def test_html_service_strips_fence_and_retries_incomplete_output_once() -> None:
    stub = TextStub(["```html\nshort\n```", f"```html\n{complete_html('Retry')}\n```"])

    result = asyncio.run(HtmlGenerationService(stub).generate("build"))

    assert result == complete_html("Retry")
    assert "previous attempt was incomplete" in stub.prompts[1]


def test_html_service_returns_complete_first_output() -> None:
    stub = TextStub([complete_html("First")])
    assert asyncio.run(HtmlGenerationService(stub).generate("build")) == complete_html("First")
    assert len(stub.prompts) == 1
