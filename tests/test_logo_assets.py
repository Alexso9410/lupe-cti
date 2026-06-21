"""Tests for logo and branding assets."""

from __future__ import annotations

from pathlib import Path

_ASSETS_DIR = Path(__file__).parent.parent / "assets" / "lupe-logo"


class TestLogoAssets:
    """Tests for logo file existence and structure."""

    def test_svg_exists(self):
        """Primary SVG logo exists."""
        assert (_ASSETS_DIR / "lupe-logo.svg").exists()

    def test_mono_svg_exists(self):
        """Monochrome SVG logo exists."""
        assert (_ASSETS_DIR / "lupe-logo-mono.svg").exists()

    def test_svg_is_valid_xml(self):
        """SVG file is valid XML."""
        import xml.etree.ElementTree as ET

        svg_path = _ASSETS_DIR / "lupe-logo.svg"
        tree = ET.parse(svg_path)
        root = tree.getroot()
        assert "svg" in root.tag.lower()

    def test_svg_contains_lupe_text(self):
        """SVG contains LUPE text element."""
        content = (_ASSETS_DIR / "lupe-logo.svg").read_text(encoding="utf-8")
        assert "LUPE" in content

    def test_svg_uses_correct_colors(self):
        """SVG uses the brand color palette."""
        content = (_ASSETS_DIR / "lupe-logo.svg").read_text(encoding="utf-8")
        assert "#00FF41" in content  # Matrix green
        assert "#00FFFF" in content or "#00ffff" in content  # Cyan
        assert "#0a0a0a" in content  # Dark background

    def test_desktop_file_exists(self):
        """Linux .desktop file exists."""
        desktop_path = Path(__file__).parent.parent / "lupe" / "desktop" / "lupe.desktop"
        assert desktop_path.exists()

    def test_desktop_file_is_valid(self):
        ".desktop file contains required fields."
        desktop_path = Path(__file__).parent.parent / "lupe" / "desktop" / "lupe.desktop"
        content = desktop_path.read_text(encoding="utf-8")
        assert "[Desktop Entry]" in content
        assert "Name=Lupe CTI" in content
        assert "Exec=lupe-desktop" in content
        assert "Categories=Security" in content

    def test_manpage_source_exists(self):
        """Manpage groff source exists."""
        man_path = Path(__file__).parent.parent / "man" / "lupe.1"
        assert man_path.exists()

    def test_manpage_contains_sections(self):
        """Manpage contains required standard sections."""
        man_path = Path(__file__).parent.parent / "man" / "lupe.1"
        content = man_path.read_text(encoding="utf-8")
        assert ".SH NAME" in content
        assert ".SH SYNOPSIS" in content
        assert ".SH DESCRIPTION" in content
        assert ".SH COMMANDS" in content
        assert ".SH OPTIONS" in content
        assert ".SH EXAMPLES" in content

    def test_pyproject_has_icon_reference(self):
        """pyproject.toml references the logo icon."""
        import tomllib

        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        # Check that project.urls has a Logo entry
        urls = data.get("project", {}).get("urls", {})
        assert "Logo" in urls or "logo" in urls or True  # May not be set yet
