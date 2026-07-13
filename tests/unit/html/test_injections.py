from launchkit.html import AOS_FAILSAFE, inject_aos_failsafe, inject_favicon


def test_aos_failsafe_injects_before_first_lowercase_body_close() -> None:
    html = "<body>Visible</body><template></body></template>"

    repaired = inject_aos_failsafe(html)

    assert repaired == f"<body>Visible{AOS_FAILSAFE}\n</body><template></body></template>"


def test_aos_failsafe_appends_when_exact_body_close_is_absent() -> None:
    assert inject_aos_failsafe("<BODY>Visible</BODY>") == ("<BODY>Visible</BODY>" + AOS_FAILSAFE)


def test_favicon_injection_is_case_insensitive_and_non_destructive() -> None:
    html = "<HTML><HEAD><title>Demo</title></HEAD><body></body></HTML>"
    expected = '<HTML><HEAD><title>Demo</title><link rel="icon" href="/logo.png">\n</head>'

    assert inject_favicon(html, "/logo.png").startswith(expected)
    existing = "<head><link REL='ICON' href='/existing.ico'></head>"
    assert inject_favicon(existing, "/logo.png") == existing


def test_favicon_is_prepended_when_head_close_is_absent() -> None:
    assert inject_favicon("<body>Demo</body>", "/logo.png") == (
        '<link rel="icon" href="/logo.png">\n<body>Demo</body>'
    )
