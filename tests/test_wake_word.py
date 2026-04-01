"""Tests for wake-word matching helpers."""

import unittest

from app.speech.wake_word import detect_wake_phrase


class WakeWordTests(unittest.TestCase):
    """Verify practical wake-word matching variants."""

    def test_detect_wake_phrase_accepts_spaced_maki_bot_variant(self) -> None:
        """Speech recognition often inserts a space in 'makibot'."""
        matched, remainder = detect_wake_phrase("hey maki bot open chrome")

        self.assertTrue(matched)
        self.assertEqual(remainder, "open chrome")

    def test_detect_wake_phrase_accepts_phrase_only_variant(self) -> None:
        """A spaced wake phrase alone should still count as a match."""
        matched, remainder = detect_wake_phrase("okay maki bot")

        self.assertTrue(matched)
        self.assertEqual(remainder, "")

    def test_detect_wake_phrase_accepts_partial_prefix_as_wake_only(self) -> None:
        """Clipped transcriptions like 'hey ma' should still arm wake mode."""
        matched, remainder = detect_wake_phrase("hey ma")

        self.assertTrue(matched)
        self.assertEqual(remainder, "")

    def test_detect_wake_phrase_accepts_plain_maki_phrase(self) -> None:
        """The new assistant name should work as the default wake phrase."""
        matched, remainder = detect_wake_phrase("hey maki open chrome")

        self.assertTrue(matched)
        self.assertEqual(remainder, "open chrome")


if __name__ == "__main__":
    unittest.main()
