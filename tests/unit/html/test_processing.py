import hashlib
from pathlib import Path

from launchkit.html import AOS_FAILSAFE, postprocess_html

FIXTURES = Path(__file__).parents[2] / "fixtures"


def test_postprocess_html_composes_haseeb_repairs_in_source_order() -> None:
    html = (FIXTURES / "html_postprocess_input.html").read_text(encoding="utf-8")

    repaired = postprocess_html(
        html,
        order_page_href="book-a-demo.html",
        favicon_href="/assets/logo.png",
    )

    assert '<a href="book-a-demo.html"><span>Book now</span></a>' in repaired
    assert "window.location.href='book-a-demo.html'" in repaired
    assert "breadcrumb" not in repaired.lower()
    assert 'class="secondary"' not in repaired
    assert repaired.count('src="/assets/hero.jpg"') == 1
    assert '<link rel="icon" href="/assets/logo.png">\n</head>' in repaired
    assert f"{AOS_FAILSAFE}\n</body>" in repaired
    assert 'class="py-13"' in repaired
    assert hashlib.sha256(repaired.encode()).hexdigest() == (
        "fab712cd400ee690b44080cee339b71a665e0f4049593f0f90178a5e2782fbd8"
    )


def test_postprocess_html_can_enable_karim_tailwind_compatibility() -> None:
    repaired = postprocess_html(
        '<html><body><main class="py-13">Content</main></body></html>',
        order_page_href="contact.html",
        normalize_tailwind=True,
    )

    assert 'class="py-14"' in repaired
    assert 'rel="icon"' not in repaired
