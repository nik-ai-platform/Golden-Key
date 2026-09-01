from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"

FORBIDDEN_PATTERNS = (
    "NikScore(",
    "insert into nik_scores",
    "update nik_scores",
    "delete from nik_scores",
)


def test_application_has_no_legacy_nikscore_write_paths():
    offenders: list[str] = []

    for path in APP_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()

        for pattern in FORBIDDEN_PATTERNS:
            haystack = (
                source.replace("class NikScore(", "class LegacyNikScoreModel(")
                if pattern == "NikScore("
                else lowered
            )
            needle = pattern if pattern == "NikScore(" else pattern.lower()

            if needle in haystack:
                offenders.append(f"{path.relative_to(APP_ROOT)}: {pattern}")

    assert offenders == [], (
        "Legacy NikScore write path detected:\n"
        + "\n".join(offenders)
    )