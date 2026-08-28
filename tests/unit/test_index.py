from pathlib import Path

import pytest

from marketing_os.core import atomic as atomic_module
from marketing_os.core.catalog import build_catalog
from marketing_os.core.index import (
    GENERATED,
    GLOBAL_MIN_DOCS,
    INLINE_MAX,
    apply_indexes,
    discover_folders,
    plan_indexes,
    status_repo,
    sync_repo,
)
from marketing_os.core.schema import config_text

TODAY = "2026-08-20"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _doc(title: str, description: str) -> str:
    return (
        f"---\ntitle: {title}\ntype: knowledge\ndescription: {description}\n"
        f"date: {TODAY}\nstatus: active\nproduced_by: test\n---\n\n# {title}\n\n{description}\n"
    )


def _seed(root: Path, count: int, folder: str = "knowledge/wiki") -> None:
    _write(root / ".mos" / "config.yaml", config_text("Example Business"))
    for number in range(count):
        _write(
            root / folder / f"page-{number:03d}.md",
            _doc(f"Page {number}", f"Summary for page {number} about channel {number % 5}."),
        )


def test_discover_folders_ignores_thin_folders(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _seed(root, 3)
    _write(root / "content" / "only.md", _doc("Only", "A single content document."))
    folders = discover_folders(build_catalog(root))
    assert folders == ["knowledge"]


def test_small_corpus_generates_only_the_root_index(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _seed(root, 5)
    result = sync_repo(root, apply=True)
    assert result["applied"] == ["_index.md"]
    assert any(item["code"] == "small-corpus" for item in result["findings"])
    assert not (root / "knowledge" / "_index.md").exists()


def test_sync_generates_the_hierarchy_above_the_floor(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _seed(root, GLOBAL_MIN_DOCS + 5)
    result = sync_repo(root, apply=True)
    assert set(result["applied"]) == {"knowledge/_index.md", "_index.md"}
    root_text = (root / "_index.md").read_text(encoding="utf-8")
    assert GENERATED in root_text
    assert "[[knowledge/_index|knowledge/]]" in root_text
    folder_text = (root / "knowledge" / "_index.md").read_text(encoding="utf-8")
    assert "Summary for page 0 about channel 0." in folder_text
    assert "[[knowledge/wiki/page-000]]" in folder_text


def test_root_index_stays_within_the_navigation_budget(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _seed(root, 60)
    _seed(root, 60, folder="content/notes")
    sync_repo(root, apply=True)
    assert (root / "_index.md").stat().st_size < 2048


def test_large_folder_explodes_into_child_indexes(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _write(root / ".mos" / "config.yaml", config_text("Example Business"))
    for group in ("alpha", "beta"):
        for number in range(INLINE_MAX):
            _write(
                root / "knowledge" / group / f"page-{number:03d}.md",
                _doc(f"{group} {number}", f"Notes on {group} topic {number}."),
            )
    result = sync_repo(root, apply=True)
    assert "knowledge/alpha/_index.md" in result["applied"]
    assert "knowledge/beta/_index.md" in result["applied"]
    parent = (root / "knowledge" / "_index.md").read_text(encoding="utf-8")
    assert "| group | documents | covers |" in parent
    assert "[[knowledge/alpha/_index|alpha/]]" in parent


def test_plan_does_not_write(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _seed(root, GLOBAL_MIN_DOCS + 1)
    result = sync_repo(root, apply=False)
    assert result["planned"] is True
    assert result["applied"] == []
    assert result["changes"]
    assert not (root / "_index.md").exists()


def test_hand_written_index_is_never_overwritten(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _seed(root, GLOBAL_MIN_DOCS + 1)
    _write(root / "knowledge" / "_index.md", "# Mine\n\nHand maintained.\n")
    result = sync_repo(root, apply=True)
    assert "knowledge/_index.md" not in result["applied"]
    assert any(item["code"] == "hand-written-index" for item in result["findings"])
    assert (root / "knowledge" / "_index.md").read_text(encoding="utf-8") == (
        "# Mine\n\nHand maintained.\n"
    )


def test_resync_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _seed(root, GLOBAL_MIN_DOCS + 1)
    sync_repo(root, apply=True)
    again = sync_repo(root, apply=True)
    assert again["applied"] == []
    assert again["changes"] == []


def test_plan_indexes_returns_text_without_touching_disk(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _seed(root, GLOBAL_MIN_DOCS + 1)
    writes, findings = plan_indexes(root, build_catalog(root), TODAY)
    assert findings == []
    assert {item["relative"] for item in writes} == {"knowledge/_index.md", "_index.md"}
    assert all(item["action"] == "create" for item in writes)
    assert not (root / "_index.md").exists()


def test_index_status_reports_catalog_freshness(tmp_path: Path) -> None:
    root = tmp_path / "brain"
    _seed(root, GLOBAL_MIN_DOCS + 1)
    result = status_repo(root)
    assert result["schema"] == "mos.index-status.v1"
    assert any(item["code"] == "no-catalog" for item in result["findings"])
    assert result["percent"]["frontmatter"] == 100
    assert result["root_index"] is False


# --- an index write either happens or does not ---------------------------------------


def _synced_root_index(tmp_path: Path) -> Path:
    """A brain with a generated root index already on disk."""
    root = tmp_path / "brain"
    _seed(root, GLOBAL_MIN_DOCS + 5)
    sync_repo(root, apply=True)
    target = root / "_index.md"
    assert target.read_bytes()
    return target


def _replacement(text: str) -> list[dict[str, object]]:
    return [{"relative": "_index.md", "text": text, "action": "update"}]


def test_a_failed_index_write_leaves_the_index_exactly_as_it_was(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The last step is a rename over the target, so a crash cannot truncate the map."""
    target = _synced_root_index(tmp_path)
    before = target.read_bytes()

    def explode(source: object, destination: object) -> None:
        raise OSError("the disk went away mid-write")

    monkeypatch.setattr(atomic_module.os, "replace", explode)
    with pytest.raises(OSError):
        apply_indexes(target.parent, _replacement("# replaced\n"))

    assert target.read_bytes() == before
    assert list(target.parent.glob("._index.md.*")) == []  # and no scratch file left behind


def test_an_index_that_cannot_be_encoded_never_empties_the_one_on_disk(tmp_path: Path) -> None:
    """A lone surrogate is the only thing a ``str`` can hold that UTF-8 cannot write.

    An index quotes the path of every document it lists, and a filename holding bytes that
    are not valid UTF-8 decodes to exactly that. A truncating write would have emptied the
    map before discovering it could not be written.
    """
    target = _synced_root_index(tmp_path)
    before = target.read_bytes()

    with pytest.raises(UnicodeEncodeError):
        apply_indexes(target.parent, _replacement("# index\n\n- [[bad\udcffdir/page]]\n"))

    assert target.read_bytes() == before
    assert list(target.parent.glob("._index.md.*")) == []
