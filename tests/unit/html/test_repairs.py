from launchkit.html import fix_ctas, fix_duplicate_images, strip_breadcrumbs


def test_fix_ctas_matches_haseeb_anchor_and_button_behavior() -> None:
    html = """<main>
<a href="#">Read more</a><a href='#'>Contact</a><a href="">Buy now</a>
<a class="cta" href="#pricing"><span>Get started</span></a>
<a href="#team">Meet the team</a>
<button class="primary">Book a call</button>
<button onclick="openForm()">Contact</button>
<button type="submit">Reserve</button>
<button>Learn more</button>
</main>"""

    repaired = fix_ctas(html, "book.html")

    assert '<a href="book.html">Read more</a>' in repaired
    assert "<a href='book.html'>Contact</a>" in repaired
    assert '<a href="book.html">Buy now</a>' in repaired
    assert '<a class="cta" href="book.html"><span>Get started</span></a>' in repaired
    assert '<a href="#team">Meet the team</a>' in repaired
    assert "onclick=\"window.location.href='book.html'\"" in repaired
    assert '<button onclick="openForm()">Contact</button>' in repaired
    assert '<button type="submit">Reserve</button>' in repaired
    assert "<button>Learn more</button>" in repaired


def test_fix_duplicate_images_replaces_every_repeated_source() -> None:
    html = (
        '<img src="https://img.example/one.jpg" alt="one">'
        '<img alt="again" src="https://img.example/one.jpg">'
        '<img src="/assets/two.jpg"><img src="/assets/two.jpg">'
        '<img alt="no source">'
    )

    repaired = fix_duplicate_images(html)

    assert repaired.count("<img") == 3
    assert repaired.count('aria-hidden="true"') == 2
    assert repaired.startswith('<img src="https://img.example/one.jpg"')
    assert repaired.endswith('<img alt="no source">')


def test_strip_breadcrumbs_removes_bars_and_extra_nav_but_keeps_footer_nav() -> None:
    html = """<body>
<nav id="primary">Primary</nav>
<div class="breadcrumb trail">Crumbs</div>
<ol aria-label="breadcrumb"><li>Crumbs</li></ol>
<nav id="secondary">Secondary</nav>
<footer><nav id="footer">Footer</nav></footer>
</body>"""

    repaired = strip_breadcrumbs(html)

    assert "breadcrumb" not in repaired.lower()
    assert 'id="primary"' in repaired
    assert 'id="secondary"' not in repaired
    assert 'id="footer"' in repaired


def test_strip_breadcrumbs_handles_single_or_missing_navigation() -> None:
    single = "<nav>Only navigation</nav><main>Content</main>"
    no_navigation = '<div aria-label="breadcrumb">Crumbs</div><main>Content</main>'

    assert strip_breadcrumbs(single) == single
    assert strip_breadcrumbs(no_navigation) == "<main>Content</main>"
