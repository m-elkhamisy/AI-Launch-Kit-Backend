from launchkit.html import fix_tailwind_classes


def test_tailwind_normalization_matches_karim_scale_and_variants() -> None:
    html = (
        '<div class="py-13 lg:hover:mt-13.5 gap-18 w-32 text-13 '
        'text-500 grid-cols-13 z-13 max-w-7xl">Demo</div>'
    )

    repaired = fix_tailwind_classes(html)

    assert 'class="py-14 lg:hover:mt-14 gap-20 w-32 text-14 ' in repaired
    assert "text-500" in repaired
    assert "grid-cols-13" in repaired
    assert "z-13" in repaired
    assert "max-w-7xl" in repaired


def test_tailwind_ties_snap_up_and_valid_fractional_values_remain() -> None:
    assert fix_tailwind_classes('class="p-3.5 mt-13"') == 'class="p-3.5 mt-14"'
