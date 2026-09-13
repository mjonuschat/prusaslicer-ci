import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_changelog  # noqa: E402


SAMPLE = """# Changelog

Intro text.

## Unreleased

### Added

- New thing.

### Changed

### Fixed

- Fixed a bug.

### Ported

- Ported a feature.

## 1.2.3 - 2026-01-01

### Added

- Old thing.
"""


class ExtractUnreleasedTests(unittest.TestCase):
    def test_extracts_body_between_unreleased_and_next_heading(self):
        body = extract_changelog.extract_unreleased(SAMPLE)
        self.assertIn("- New thing.", body)
        self.assertIn("- Fixed a bug.", body)
        self.assertIn("- Ported a feature.", body)
        self.assertNotIn("- Old thing.", body)
        self.assertNotIn("Intro text.", body)

    def test_missing_heading_raises(self):
        with self.assertRaises(ValueError):
            extract_changelog.extract_unreleased("# Changelog\n\nNo unreleased section.\n")

    def test_empty_unreleased_section_raises(self):
        text = "# Changelog\n\n## Unreleased\n\n### Added\n\n## 1.0.0 - 2026-01-01\n"
        with self.assertRaises(ValueError):
            extract_changelog.extract_unreleased(text)

    def test_unreleased_at_end_of_file_with_no_following_heading(self):
        text = "# Changelog\n\n## Unreleased\n\n- Only entry.\n"
        body = extract_changelog.extract_unreleased(text)
        self.assertIn("- Only entry.", body)


class BumpUnreleasedTests(unittest.TestCase):
    def test_renames_heading_to_versioned_section(self):
        result = extract_changelog.bump_unreleased(SAMPLE, "2.0.0", "2026-03-01")
        self.assertIn("## 2.0.0 - 2026-03-01", result)
        self.assertIn("- New thing.", result)

    def test_inserts_fresh_unreleased_scaffold_above_versioned_section(self):
        result = extract_changelog.bump_unreleased(SAMPLE, "2.0.0", "2026-03-01")
        unreleased_idx = result.index("## Unreleased")
        versioned_idx = result.index("## 2.0.0 - 2026-03-01")
        self.assertLess(unreleased_idx, versioned_idx)
        scaffold = result[unreleased_idx:versioned_idx]
        self.assertIn("### Added", scaffold)
        self.assertIn("### Changed", scaffold)
        self.assertIn("### Fixed", scaffold)
        self.assertIn("### Ported", scaffold)
        self.assertNotIn("- New thing.", scaffold)

    def test_preserves_older_sections_unchanged(self):
        result = extract_changelog.bump_unreleased(SAMPLE, "2.0.0", "2026-03-01")
        self.assertIn("## 1.2.3 - 2026-01-01", result)
        self.assertIn("- Old thing.", result)

    def test_preserves_intro_text_unchanged(self):
        result = extract_changelog.bump_unreleased(SAMPLE, "2.0.0", "2026-03-01")
        self.assertIn("Intro text.", result)

    def test_empty_unreleased_section_raises(self):
        text = "# Changelog\n\n## Unreleased\n\n### Added\n\n## 1.0.0 - 2026-01-01\n"
        with self.assertRaises(ValueError):
            extract_changelog.bump_unreleased(text, "2.0.0", "2026-03-01")


class MainCliTests(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent / "extract_changelog.py"), *args],
            capture_output=True,
            text=True,
        )

    def test_writes_extracted_body_to_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(SAMPLE, encoding="utf-8")
            output = Path(tmp) / "out.md"

            result = self._run(str(changelog), "--output", str(output))

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("- New thing.", output.read_text(encoding="utf-8"))

    def test_bump_rewrites_changelog_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(SAMPLE, encoding="utf-8")
            output = Path(tmp) / "out.md"

            result = self._run(
                str(changelog), "--output", str(output),
                "--bump", "2.0.0", "--date", "2026-03-01",
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("- New thing.", output.read_text(encoding="utf-8"))
            rewritten = changelog.read_text(encoding="utf-8")
            self.assertIn("## 2.0.0 - 2026-03-01", rewritten)
            self.assertIn("## Unreleased", rewritten)

    def test_missing_unreleased_section_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text("# Changelog\n\nNothing here.\n", encoding="utf-8")
            output = Path(tmp) / "out.md"

            result = self._run(str(changelog), "--output", str(output))

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


class RealChangelogSampleTests(unittest.TestCase):
    """Parses a real snapshot of BOSS's release-notes CHANGELOG.md to
    catch formatting the synthetic SAMPLE fixture doesn't exercise."""

    def setUp(self):
        self.text = (Path(__file__).resolve().parent / "testdata" / "real_changelog_sample.md").read_text(
            encoding="utf-8"
        )

    def test_extracts_without_error(self):
        body = extract_changelog.extract_unreleased(self.text)
        self.assertTrue(body.strip())

    def test_bumps_without_error(self):
        result = extract_changelog.bump_unreleased(self.text, "3.0.0", "2026-09-13")
        self.assertIn("## 3.0.0 - 2026-09-13", result)
        self.assertIn("## Unreleased", result)


if __name__ == "__main__":
    unittest.main()
