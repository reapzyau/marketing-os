"""Discovery has to be right in both directions.

Finding an answer that is filed somewhere unexpected is the point of the module, but
inventing one is worse than missing one: a brain that claims to know its own proof when the
file says "Status: Gap" will speak with a confidence it has not earned. So these tests pin
both halves — what gets found, and what stays missing — plus the tie-breaks that decide
between two plausible files, because a dashboard that ranks differently on every refresh is
not a dashboard anyone can act on.
"""

from pathlib import Path

import pytest

from marketing_os.core.discover import MIN_CONFIDENCE, NAV_FILES, normalise, resolve_field

VOICE = (
    "# Voice\n\n"
    "Precision-led and evidence-based. Every sentence earns its place, and nothing is "
    "claimed here that cannot be shown.\n"
)
BRAND = (
    "# Brand\n\n"
    "The operator's brain for marketing work: plain language, shown workings, and no "
    "claim that outruns the evidence.\n"
)
OFFER = (
    "# What we sell\n\n"
    "A six week build-along for marketers who want the system installed rather than "
    "explained, at a fixed price.\n"
)
AUDIENCE = (
    "# Avatar\n\n"
    "Marketers running their own delivery who have tried the tools, kept none of them, "
    "and want one system that holds.\n"
)
STRATEGY = (
    "# Roadmap\n\n"
    "Win the operators who already build in public, then let their published systems do "
    "the selling for the rest.\n"
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _symlink(link: Path, target: Path) -> None:
    """Create a directory symlink, or skip the test on a filesystem that has none."""
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):  # pragma: no cover - platform dependent
        pytest.skip("this filesystem does not support symlinks")


# --- the exact hit ------------------------------------------------------------------


def test_a_substantive_canonical_file_wins_without_being_scored(tmp_path: Path) -> None:
    canonical = tmp_path / "business/brand/brand.md"
    _write(canonical, BRAND)
    _write(tmp_path / "reference/core/brand.md", BRAND)

    result = resolve_field(tmp_path, "brand", canonical)

    assert result.source == "canonical"
    assert result.path == canonical
    assert result.confidence == 100
    # Nothing was scored: the rival copy in reference/ was never even looked at.
    assert result.considered == 0


# --- discovery ----------------------------------------------------------------------


def test_content_at_a_non_canonical_path_is_discovered(tmp_path: Path) -> None:
    found = tmp_path / "reference/core/voice.md"
    _write(found, VOICE)

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.source == "discovered"
    assert result.path == found
    # 50 for the file's own name being the field's, 5 for sitting two folders below its root.
    assert result.confidence == 55
    assert result.considered == 1


def test_singular_offer_folder_answers_for_an_empty_canonical_offers(tmp_path: Path) -> None:
    """The trap a real brain fell into: the canonical folder is plural and empty.

    ``pricing.md`` is a word the offer field is known by, so the file's own name is what makes
    it a candidate; the folder is what makes it a convincing one, and it can only do that
    once ``offers`` and ``offer`` are read as the same word. The exact score is pinned so the
    folder's thirty points cannot quietly stop counting.
    """
    (tmp_path / "business/offers").mkdir(parents=True)
    (tmp_path / "business/offers/.gitkeep").write_text("", encoding="utf-8")
    found = tmp_path / "business/offer/pricing.md"
    _write(found, OFFER)

    result = resolve_field(tmp_path, "offer", tmp_path / "business/offers/offer.md")

    assert result.source == "discovered"
    assert result.path == found
    assert result.confidence >= MIN_CONFIDENCE
    # 30 for the name being one the field is known by, 30 for the folder, 5 for the depth.
    assert result.confidence == 65


def test_a_file_without_frontmatter_is_discovered_on_naming_alone(tmp_path: Path) -> None:
    found = tmp_path / "business/audience/avatar.md"
    _write(found, AUDIENCE)
    assert not found.read_text(encoding="utf-8").startswith("---")

    result = resolve_field(tmp_path, "audience", tmp_path / "business/audience/primary.md")

    assert result.source == "discovered"
    assert result.path == found


# --- what stays missing -------------------------------------------------------------


def test_boilerplate_below_the_substantive_threshold_stays_missing(tmp_path: Path) -> None:
    _write(tmp_path / "reference/core/voice.md", "# Voice\n\nShort and unfinished.\n")
    canonical = tmp_path / "business/brand/voice.md"

    result = resolve_field(tmp_path, "voice", canonical)

    assert result.source == "missing"
    assert result.path == canonical
    assert result.confidence == 0
    assert result.considered == 0


def test_an_archived_copy_never_answers_for_a_live_one(tmp_path: Path) -> None:
    live = tmp_path / "reference/brand/voice.md"
    _write(live, VOICE)
    _write(tmp_path / "reference/brand/_archive/voice.md", VOICE)

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.path == live
    # The archived copy was excluded outright, not merely out-scored.
    assert result.considered == 1


# --- ranking ------------------------------------------------------------------------


def test_an_underscore_folder_loses_to_an_equal_file_beside_it(tmp_path: Path) -> None:
    """Both paths are the same length and the working copy sorts first, so only the
    underscore penalty can decide this one."""
    live = tmp_path / "reference/core/voice.md"
    _write(live, VOICE)
    _write(tmp_path / "reference/_wip/voice.md", VOICE)

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.path == live
    assert result.confidence == 55
    assert result.considered == 2


def test_a_stale_document_is_refused_outright_not_merely_out_scored(tmp_path: Path) -> None:
    """The stale file has the shorter path, so it would win every tie-break there is."""
    fresh = tmp_path / "reference/core/voice.md"
    _write(fresh, "---\nstatus: active\n---\n" + VOICE)
    _write(tmp_path / "reference/alt/voice.md", "---\nstatus: stale\n---\n" + VOICE)

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.path == fresh
    # Excluded, not out-scored: a document that says it has been left behind is taken at its
    # word, which a thirty-point deduction never managed against perfect naming.
    assert result.considered == 1


def test_a_stale_document_never_answers_even_with_no_rival(tmp_path: Path) -> None:
    """The case the losing-to-a-rival test could never reach: it is the only candidate."""
    canonical = tmp_path / "business/brand/voice.md"
    for status in ("archived", "superseded", "deprecated", "stale"):
        _write(tmp_path / "business/brand/voice/voice.md", f"---\nstatus: {status}\n---\n" + VOICE)

        result = resolve_field(tmp_path, "voice", canonical)

        assert result.source == "missing", status
        assert result.considered == 0, status


# --- safety -------------------------------------------------------------------------


def test_a_symlink_cycle_terminates_without_double_counting(tmp_path: Path) -> None:
    found = tmp_path / "business/strategy/roadmap.md"
    _write(found, STRATEGY)
    _symlink(tmp_path / "business/strategy/loop", tmp_path / "business/strategy")
    _symlink(tmp_path / "mirror", tmp_path / "business")

    result = resolve_field(tmp_path, "strategy", tmp_path / "business/strategy/strategy.md")

    assert result.source == "discovered"
    assert result.path == found
    # One file, reachable three ways: through the cycle, through the mirror, and directly.
    assert result.considered == 1


def test_an_unreadable_file_is_skipped_rather_than_raising(tmp_path: Path) -> None:
    canonical = tmp_path / "business/brand/voice.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_bytes(b"---\ntitle: Voice\n---\n\xff\xfe not valid utf-8 at all\n")
    (tmp_path / "reference/core").mkdir(parents=True)
    (tmp_path / "reference/core/tone.md").write_bytes(b"\xff\xfe also unreadable\n")
    found = tmp_path / "reference/core/voice.md"
    _write(found, VOICE)

    result = resolve_field(tmp_path, "voice", canonical)

    assert result.source == "discovered"
    assert result.path == found
    assert result.considered == 1


def test_resolution_is_identical_across_repeated_calls(tmp_path: Path) -> None:
    _write(tmp_path / "reference/core/voice.md", VOICE)
    _write(tmp_path / "reference/brand/tone.md", VOICE)
    _write(tmp_path / "reference/_wip/voice.md", VOICE)
    _write(tmp_path / "business/brand/writing-style.md", VOICE)
    _write(tmp_path / "business/brand/guidelines/tone-of-voice.md", VOICE)

    results = [
        resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md") for _ in range(5)
    ]

    # Resolution is frozen, so an identical run collapses to one member of the set.
    assert len(set(results)) == 1
    assert results[0].source == "discovered"


# --- normalisation ------------------------------------------------------------------


def test_normalise_reduces_the_spellings_an_operator_actually_uses() -> None:
    assert normalise("offers") == normalise("offer") == "offer"
    assert normalise("Offer_Definition.md") == "offer-definition"
    assert normalise("okrs") == "okr"
    assert normalise("_shared") == "shared"
    # Two characters left is too little to be a plural: ``ops`` is a word, ``op`` is a guess.
    assert normalise("ops") == "ops"


# --- navigation and machinery are never answers -------------------------------------


def test_a_generated_index_never_answers_for_the_folder_it_indexes(tmp_path: Path) -> None:
    """The cheapest false positive there is: a file this program writes itself.

    ``mos index sync`` puts an ``_index.md`` in every folder holding documents, and
    ``/mos-end`` tells the operator to run it at the end of every session. Sitting directly
    in ``business/audience/``, it used to clear the confidence bar on placement alone — so a
    brain whose every context file was still a TODO stub could report four fields answered
    without one word of business truth being written.
    """
    _write(
        tmp_path / "business/audience/_index.md",
        "# business/audience/ — index\n\n"
        "*Generated by `mos index sync` — do not hand-edit.*\n\n"
        "- [[business/audience/agency-owner/profile]] — the agency owner segment\n"
        "- [[business/audience/solopreneur/profile]] — the solo creator segment\n",
    )

    result = resolve_field(tmp_path, "audience", tmp_path / "business/audience/primary.md")

    assert result.source == "missing"
    assert result.considered == 0


def test_a_hand_written_index_never_answers_for_the_folder_it_indexes(tmp_path: Path) -> None:
    """The same file without the marker that gives the generated one away.

    An operator who writes their own ``_index.md`` produces a page of real prose with no
    ``Generated by`` line anywhere in it, so the marker rule cannot see it and the substance
    rule has nothing to object to. It is still a map of the folder rather than the answer the
    folder was supposed to hold, and the only thing that can tell the difference cheaply is
    that no field is known by the word ``index``.
    """
    _write(
        tmp_path / "business/audience/_index.md",
        "# Audience\n\nThe four segments we sell to, and where each one's profile is kept. "
        "Agency owners and solo creators come first; the in-house marketers are a later "
        "push, once the community is big enough to reach them.\n",
    )

    result = resolve_field(tmp_path, "audience", tmp_path / "business/audience/primary.md")

    assert result.source == "missing"
    assert result.considered == 0


def test_a_folder_readme_never_answers_for_the_folder_it_describes(tmp_path: Path) -> None:
    """A map of a folder is not the thing the folder was supposed to contain.

    The real brain this was found on had a ``business/proof/README.md`` whose own text said
    the proof buckets were still empty, and it out-scored the actual testimonials document.
    """
    _write(
        tmp_path / "business/proof/README.md",
        "# Proof\n\nOne file per kind of evidence. Most buckets here are forward-looking: "
        "the community is too new for a deep testimonial library yet.\n",
    )

    result = resolve_field(tmp_path, "proof", tmp_path / "business/proof/testimonials.md")

    assert result.source == "missing"
    assert result.considered == 0


def test_the_real_file_one_level_down_wins_the_folder_its_readme_describes(
    tmp_path: Path,
) -> None:
    """Both halves of the proof failure in one tree: the map is refused, the answer is found.

    Refusing the map is only half a fix. On the brain this was found on the README beat
    ``business/proof/testimonials/testimonials.md``, which is the document somebody actually
    sat down and wrote, so the test that matters is not only that the map loses but that the
    file below it wins and is the path handed back for an operator to open.
    """
    _write(
        tmp_path / "business/proof/README.md",
        "# Proof\n\nOne file per kind of evidence: testimonials, case studies and reviews. "
        "Most of the buckets here are still forward-looking.\n",
    )
    found = tmp_path / "business/proof/testimonials/testimonials.md"
    _write(
        found,
        "# Testimonials\n\nMembers who rebuilt their own delivery on the system and said so "
        "in writing, quoted with the result they got and the month they got it.\n",
    )

    result = resolve_field(tmp_path, "proof", tmp_path / "business/proof/testimonials.md")

    assert result.source == "discovered"
    assert result.path == found
    # The README was never opened, let alone scored: one candidate, and it is the real one.
    assert result.considered == 1


@pytest.mark.parametrize("filename", sorted(NAV_FILES))
def test_no_navigation_file_answers_even_when_its_name_becomes_an_alias(
    tmp_path: Path, filename: str, monkeypatch
) -> None:
    """The belt to the name gate's braces, tested the only way it can bite.

    Today the gate already refuses every one of these, because no field is known by the word
    ``readme`` or ``log``. That is precisely why the list has to be independent of the alias
    table rather than a consequence of it: the day somebody adds ``notes`` to the words an
    audience is known by, a folder full of navigation must not start answering for the
    business. So the alias table is given the nav word here, and the file still loses.
    """
    from marketing_os.core import discover

    aliases = dict(discover.ALIASES)
    aliases["brand"] = aliases["brand"] | {normalise(filename)}
    monkeypatch.setattr(discover, "ALIASES", aliases)
    _write(tmp_path / f"business/brand/{filename}", BRAND)

    result = discover.resolve_field(tmp_path, "brand", tmp_path / "business/brand/brand.md")

    assert result.source == "missing"
    assert result.considered == 0


def test_a_document_carrying_the_generated_marker_is_refused(tmp_path: Path) -> None:
    """Names are not the only way a generated file arrives; the marker is checked too."""
    _write(
        tmp_path / "business/strategy/strategy-map.md",
        "# Strategy map\n\n*Generated by `mos index sync` — do not hand-edit.*\n\n"
        "Win the operators who already build in public, then let their systems sell.\n",
    )

    result = resolve_field(tmp_path, "strategy", tmp_path / "business/strategy/strategy.md")

    assert result.source == "missing"


# --- placement corroborates, it never decides ----------------------------------------


def test_a_file_whose_own_name_means_nothing_cannot_answer_for_its_folder(
    tmp_path: Path,
) -> None:
    """The general form of the README problem, with a file that is nobody's navigation.

    ``copy-research-bank.md`` is a real document about real work. It says nothing about how
    the business sounds, and the only reason it was ever offered as the voice answer is the
    name of the folder it happens to sit in.
    """
    _write(
        tmp_path / "business/voice/copy-research-bank.md",
        "# Copy research bank\n\nSwipe file of hooks and openers collected from competitor "
        "launches, kept for reference when drafting new campaigns.\n",
    )

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.source == "missing"
    assert result.considered == 0


def test_one_word_of_a_name_is_evidence_but_not_enough_on_its_own(tmp_path: Path) -> None:
    """``primary`` is an audience word, and a file about primary colours is not an audience.

    The token rule is what lets ``tvml-strategy.md`` be found at all, so it has to be worth
    something; it is deliberately worth less than the bar, so it always needs the folder or
    the rest of the name to agree with it.
    """
    _write(
        tmp_path / "business/brand/primary-colours.md",
        "# Primary colours\n\nThe brand palette: ink for text, a single accent for calls to "
        "action, and nothing else on any surface.\n",
    )

    result = resolve_field(tmp_path, "audience", tmp_path / "business/audience/primary.md")

    assert result.source == "missing"
    # It was scored, and it lost. That is the difference from the test above.
    assert result.considered == 1


@pytest.mark.parametrize(
    ("relative", "field", "canonical", "body"),
    [
        (
            "business/strategy/tvml-strategy.md",
            "strategy",
            "business/strategy/strategy.md",
            STRATEGY,
        ),
        ("business/offer/offer-backbone.md", "offer", "business/offers/offer.md", OFFER),
    ],
)
def test_a_hyphenated_name_is_read_as_the_words_it_is_made_of(
    tmp_path: Path, relative: str, field: str, canonical: str, body: str
) -> None:
    """Real files are named for two things at once, and the gate has to see through that.

    Both rules are needed and neither covers the other. ``offer-backbone`` is a whole name the
    offer field is known by, so the whole-stem test catches it and multi-word aliases like
    ``tone-of-voice`` keep working as units. ``tvml-strategy`` is nobody's alias — it is a
    business name welded to a field name — and only the split reaches it. Drop the split and
    a real brain's strategy document stops being found; drop the whole-stem test and every
    hyphenated alias in the table stops meaning anything.
    """
    found = tmp_path / relative
    _write(found, body)

    result = resolve_field(tmp_path, field, tmp_path / canonical)

    assert result.source == "discovered"
    assert result.path == found
    assert result.confidence >= MIN_CONFIDENCE


def test_a_page_of_todo_bullets_is_not_an_answer(tmp_path: Path) -> None:
    """The repo's own template convention, one bullet marker away from reporting complete."""
    _write(
        tmp_path / "business/brand/voice/tone.md",
        "# Voice\n\n"
        "- TODO: describe the tone in three adjectives\n"
        "- TODO: list the words this brand never uses\n"
        "- [ ] TODO: add two sentences of real writing to copy the rhythm from\n"
        "> TODO: and say who signs off on changes\n",
    )

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.source == "missing"


# --- the scan stays inside the repository --------------------------------------------


def test_a_symlink_out_of_the_repository_is_not_a_search_root(tmp_path: Path) -> None:
    """Every path this module reports is repo-relative, so it must be repo-real too."""
    outside = tmp_path / "outside"
    _write(outside / "private/voice.md", VOICE)
    root = tmp_path / "brain"
    _write(root / "business/brand/.gitkeep", "")
    _symlink(root / "vault", outside)

    result = resolve_field(root, "voice", root / "business/brand/voice.md")

    assert result.source == "missing"
    assert result.considered == 0


def test_a_symlink_to_the_parent_directory_does_not_read_sibling_repositories(
    tmp_path: Path,
) -> None:
    root = tmp_path / "brain"
    _write(root / "business/brand/.gitkeep", "")
    _write(tmp_path / "sibling-repo/business/brand/voice.md", VOICE)
    _symlink(root / "up", tmp_path)

    result = resolve_field(root, "voice", root / "business/brand/voice.md")

    assert result.source == "missing"


def test_a_self_link_does_not_expose_the_folders_the_two_roots_leave_out(
    tmp_path: Path,
) -> None:
    """``knowledge/`` is other people's writing. It is not the brain's own voice."""
    _write(tmp_path / "business/brand/.gitkeep", "")
    _write(tmp_path / "knowledge/wiki/voice.md", VOICE)
    _symlink(tmp_path / "self", tmp_path)

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.source == "missing"


def test_a_link_beside_a_folder_cannot_hide_the_folder_it_points_at(tmp_path: Path) -> None:
    """The answer must not depend on where a symlink sorts alphabetically.

    Marking a real path visited at enqueue time meant the first name to reach a directory
    kept it, and a link sorting before its own target hid the target for the rest of the
    walk. Every file under it was then scored under the link's name, which carries none of
    the folder's evidence — so an answered field reported missing, and renaming the link
    ``z-link`` answered it again.
    """
    found = tmp_path / "business/brand/voice/tone.md"
    _write(found, VOICE)
    _symlink(tmp_path / "business/brand/a-link", tmp_path / "business/brand/voice")

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.source == "discovered"
    assert result.path == found
    # One file, reachable under two names, reported under the one that is really there.
    assert result.considered == 1
    # 30 for the name, 30 for the folder it really lives in — not the 30 it scored
    # under the link's name, which is below the bar and reported the field missing.
    assert result.confidence == 60


# --- exclusions are compared in the module's own spelling ----------------------------


@pytest.mark.parametrize(
    "folder",
    ["archives", "Templates", "brain-dumps", "examples", "old", "scratch"],
)
def test_folders_that_never_hold_a_current_answer_are_excluded_in_any_spelling(
    tmp_path: Path, folder: str
) -> None:
    """The exclusion list was compared raw while every other name went through ``normalise``.

    Plural tolerance therefore ran one way only: it helped a folder match an alias and never
    helped one get excluded, so an abandoned draft in ``archives/`` spoke for the business
    while the same draft in ``archive/`` was correctly ignored.
    """
    _write(tmp_path / f"business/brand/{folder}/voice.md", VOICE)

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.source == "missing"
    assert result.considered == 0


# --- one walk, and a walk that says when it gave up ----------------------------------


def test_every_unanswered_field_is_resolved_in_a_single_pass(tmp_path: Path) -> None:
    """Six questions of one tree, walked once.

    The walk does not depend on which field is being asked about — only the alias test and
    the score do, and both are arithmetic on names already in hand. Asking per field walked
    the identical tree six times, which was the entire warm-cache cost of ``mos status``.
    """
    from marketing_os.core import discover

    for name in ("alpha", "beta", "gamma", "delta"):
        _write(tmp_path / f"business/{name}/notes.md", BRAND)
    _write(tmp_path / "reference/core/voice.md", VOICE)

    seen: list[Path] = []
    real_entries = discover._entries

    def counting(directory: Path):
        seen.append(directory)
        return real_entries(directory)

    discover._entries = counting  # noqa: SLF001 - the seam this test exists to measure
    try:
        resolved = discover.resolve_fields(
            tmp_path,
            {
                "brand": tmp_path / "business/brand/brand.md",
                "voice": tmp_path / "business/brand/voice.md",
                "audience": tmp_path / "business/audience/primary.md",
                "strategy": tmp_path / "business/strategy/strategy.md",
                "proof": tmp_path / "business/proof/testimonials.md",
            },
        )
    finally:
        discover._entries = real_entries

    assert resolved["voice"].source == "discovered"
    # business, its four subfolders, reference and reference/core: seven directories, each
    # opened exactly once no matter how many questions were asked of them.
    assert len(seen) == len(set(seen)) == 7


def test_a_scan_that_runs_out_of_budget_says_so(tmp_path: Path, monkeypatch) -> None:
    from marketing_os.core import discover

    _write(tmp_path / "reference/core/voice.md", VOICE)
    _write(tmp_path / "reference/brand/tone.md", VOICE)
    monkeypatch.setattr(discover, "FILE_BUDGET", 1)

    result = discover.resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.truncated is True


def test_a_complete_scan_does_not_claim_to_be_truncated(tmp_path: Path) -> None:
    _write(tmp_path / "reference/core/voice.md", VOICE)

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.truncated is False


def test_noise_in_one_folder_cannot_starve_the_answer_in_another(
    tmp_path: Path, monkeypatch
) -> None:
    """The budget is spent on files that might be answers, not on every file seen.

    An exported chat log dropped under ``business/`` used to consume the whole budget in
    alphabetical order and the walk stopped before reaching the real answer — which then
    reported missing, with nothing in the output saying the scan had been cut short.
    """
    from marketing_os.core import discover

    for number in range(60):
        _write(tmp_path / f"business/aaa-transcripts/entry-{number:03d}.md", "x")
    _write(tmp_path / "business/zzz/voice.md", VOICE)
    monkeypatch.setattr(discover, "FILE_BUDGET", 3)

    result = discover.resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.source == "discovered"
    assert result.truncated is False


# --- reading the file at all ---------------------------------------------------------


def test_a_byte_order_mark_does_not_hide_the_frontmatter(tmp_path: Path) -> None:
    """A file saved by Notepad begins ``\\ufeff``, which pushed the ``---`` fence off line one.

    Every frontmatter rule then silently stopped applying: the staleness marker went unread
    and an archived document scored as though it had never said anything about itself.
    """
    stale = tmp_path / "business/brand/voice/voice.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("---\nstatus: archived\n---\n" + VOICE, encoding="utf-8-sig")
    assert stale.read_bytes().startswith(b"\xef\xbb\xbf")

    result = resolve_field(tmp_path, "voice", tmp_path / "business/brand/voice.md")

    assert result.source == "missing"


def test_a_file_larger_than_the_read_limit_is_not_pulled_into_memory_whole(
    tmp_path: Path, monkeypatch
) -> None:
    """A 200-megabyte transcript under a field's folder is not read to find out it is not one."""
    from marketing_os.core import discover

    monkeypatch.setattr(discover, "READ_LIMIT", 200)
    _write(tmp_path / "business/audience/avatar.md", AUDIENCE + "\n" + ("filler. " * 5000))

    result = discover.resolve_field(tmp_path, "audience", tmp_path / "business/audience/primary.md")

    assert result.source == "discovered"


# --- normalisation ------------------------------------------------------------------


def test_normalise_reaches_the_plurals_the_alias_table_is_written_in() -> None:
    assert normalise("strategies") == "strategy"
    assert normalise("case-studies") == "case-study"
    assert normalise("identities") == "identity"
    # A word ending in a doubled s is not a plural of anything.
    assert normalise("business") == "business"
    assert normalise("process") == "process"


def test_normalise_is_idempotent_and_collides_no_two_alias_words() -> None:
    from marketing_os.core.discover import FIELD_ALIASES

    words = [word for field in FIELD_ALIASES.values() for word in field]
    for word in [*words, "strategies", "case-studies", "offers", "ops", "business"]:
        assert normalise(normalise(word)) == normalise(word), word
    for field, spellings in FIELD_ALIASES.items():
        reduced = [normalise(word) for word in spellings]
        assert len(reduced) == len(set(reduced)), field


@pytest.mark.parametrize("status", ["gap", "placeholder", "todo", "planned"])
def test_a_document_that_marks_itself_a_placeholder_is_not_an_answer(
    tmp_path: Path, status: str
) -> None:
    """The lever an operator has over discovery, for the document that records an absence.

    A proof file whose whole purpose is to say there is no proof yet is a real document by
    every mechanical test there is — right name, right folder, paragraphs of real writing.
    Nothing model-free can tell it apart from an answer except its own declaration, so the
    declaration is honoured.
    """
    _write(
        tmp_path / "business/proof/testimonials/testimonials.md",
        f"---\nstatus: {status}\n---\n\n# Testimonials\n\n"
        "None collected yet. As the community grows, collect screenshots of member wins and "
        "before-and-after results from people using the shared systems.\n",
    )

    result = resolve_field(tmp_path, "proof", tmp_path / "business/proof/testimonials.md")

    assert result.source == "missing"


def test_an_alias_on_the_file_name_and_nothing_else_stays_below_the_floor(
    tmp_path: Path,
) -> None:
    """The promise the docs make about ``business/pricing.md``, pinned.

    ``pricing`` is one of the words an offer is known by, and a file called ``pricing.md``
    sitting loose at the top of ``business/`` is the weakest case there is: one word, in the
    file name, with nothing else agreeing with it. It is scored and it loses.
    """
    _write(
        tmp_path / "business/pricing.md",
        "# Pricing\n\nOur rate card for the year, kept here so quotes stop being invented "
        "from memory on the phone.\n",
    )

    result = resolve_field(tmp_path, "offer", tmp_path / "business/offers/offer.md")

    assert result.source == "missing"
    assert result.considered == 1


# --- the scaffold an operator actually installs --------------------------------------


def test_a_folder_map_on_a_fresh_scaffold_leaves_every_field_missing(tmp_path: Path) -> None:
    """The report that started this, reproduced end to end rather than argued about.

    ``mos onboard`` writes a brain of TODO stubs. Dropping a two-sentence README into
    ``business/brand/`` — a file whose own text says nothing has been written yet — made brand
    report ``complete: true`` with ``source: discovered``, which is the worst thing this
    feature can do: tell an operator a question is answered when it is not. This walks the
    real scaffold rather than a hand-built tree, so the claim is made about the thing people
    install, and it goes through the status envelope, because that is where the operator and
    the dashboard read it.
    """
    from marketing_os.core.setup import setup_repo
    from marketing_os.core.status import status_repo

    root = tmp_path / "brain"
    setup_repo(root, "Example Business", "all", mode="in-house", apply=True)
    for folder in ("brand", "audience", "offers", "proof", "strategy"):
        _write(
            root / f"business/{folder}/README.md",
            f"# {folder.title()}\n\nOne file per part of the {folder}, kept together so the "
            "whole picture sits in one place. Nothing has been written here yet.\n",
        )

    status = status_repo(root)

    fields = status["context"]["fields"]
    assert fields, "the status envelope reported no context fields at all"
    assert all(entry["source"] == "missing" for entry in fields.values())
    assert not any("discovered_path" in entry for entry in fields.values())
    assert all(entry["complete"] is False for entry in fields.values())
    assert status["context"]["missing"] == ["brand", "voice", "audience", "offer"]
    assert status["repo_state"] == "needs-context"
