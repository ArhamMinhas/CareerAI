import uuid

from app.models.learning_path import RoadmapPhase
from app.services.learning_roadmap import _bucket_into_phases, _topological_sort

# Pure-function tests — no DB, no fixtures. Named skill ids for readability; real ids are UUIDs
# in production but the algorithm only cares about equality/hashing, so any hashable works.


def _ids(*names: str) -> dict[str, uuid.UUID]:
    return {name: uuid.uuid4() for name in names}


def test_topological_sort_respects_a_linear_chain() -> None:
    ids = _ids("python", "ml", "deep_learning")
    # deep_learning requires ml requires python: edges are (skill, requires_skill).
    edges = [(ids["ml"], ids["python"]), (ids["deep_learning"], ids["ml"])]
    priority = {ids["python"]: 1, ids["ml"]: 1, ids["deep_learning"]: 1}

    order = _topological_sort(list(ids.values()), edges, priority)

    assert order.index(ids["python"]) < order.index(ids["ml"])
    assert order.index(ids["ml"]) < order.index(ids["deep_learning"])


def test_topological_sort_respects_a_diamond_with_priority_tiebreak() -> None:
    ids = _ids("a", "b", "c", "d")
    # d requires b and c; b and c both require a.
    edges = [
        (ids["b"], ids["a"]),
        (ids["c"], ids["a"]),
        (ids["d"], ids["b"]),
        (ids["d"], ids["c"]),
    ]
    # b outranks c so, once both are ready, b must come first.
    priority = {ids["a"]: 5, ids["b"]: 10, ids["c"]: 1, ids["d"]: 5}

    order = _topological_sort(list(ids.values()), edges, priority)

    assert order[0] == ids["a"]
    assert order.index(ids["b"]) < order.index(ids["c"])
    assert order[-1] == ids["d"]


def test_topological_sort_falls_back_to_priority_when_no_edges() -> None:
    ids = _ids("low", "high", "mid")
    priority = {ids["low"]: 1, ids["high"]: 10, ids["mid"]: 5}

    order = _topological_sort(list(ids.values()), [], priority)

    assert order == [ids["high"], ids["mid"], ids["low"]]


def test_topological_sort_survives_a_real_cycle_without_crashing() -> None:
    """A<->B is a genuine cycle — real curated data shouldn't have one, but the algorithm must
    never infinite-loop or raise; it falls back to priority order for the unresolvable skills."""
    ids = _ids("a", "b", "c")
    edges = [(ids["a"], ids["b"]), (ids["b"], ids["a"])]  # a requires b, b requires a
    priority = {ids["a"]: 1, ids["b"]: 1, ids["c"]: 10}

    order = _topological_sort(list(ids.values()), edges, priority)

    assert sorted(order) == sorted(ids.values())  # every skill still appears exactly once
    assert ids["c"] in order  # the unrelated, cycle-free skill is unaffected


def test_topological_sort_handles_empty_input() -> None:
    assert _topological_sort([], [], {}) == []


def test_bucket_into_phases_empty() -> None:
    assert _bucket_into_phases([]) == {}


def test_bucket_into_phases_single_skill_is_foundations() -> None:
    skill_id = uuid.uuid4()
    assert _bucket_into_phases([skill_id]) == {skill_id: RoadmapPhase.FOUNDATIONS}


def test_bucket_into_phases_three_skills_one_per_phase() -> None:
    ids = [uuid.uuid4() for _ in range(3)]
    phases = _bucket_into_phases(ids)
    assert phases[ids[0]] == RoadmapPhase.FOUNDATIONS
    assert phases[ids[1]] == RoadmapPhase.CORE
    assert phases[ids[2]] == RoadmapPhase.ADVANCED


def test_bucket_into_phases_ten_skills_distributes_by_position() -> None:
    ids = [uuid.uuid4() for _ in range(10)]
    phases = _bucket_into_phases(ids)
    counts = {phase: sum(1 for p in phases.values() if p == phase) for phase in RoadmapPhase}
    assert sum(counts.values()) == 10
    assert counts[RoadmapPhase.FOUNDATIONS] > 0
    # Position-based: the first skill is always Foundations, the last is never Foundations.
    assert phases[ids[0]] == RoadmapPhase.FOUNDATIONS
    assert phases[ids[-1]] != RoadmapPhase.FOUNDATIONS


def test_bucket_into_phases_is_purely_positional_not_priority_based() -> None:
    """Bucketing must depend only on `_topological_sort`'s output order, never re-derive its own
    notion of importance — otherwise phase grouping and sequence order could disagree."""
    ids = [uuid.uuid4() for _ in range(6)]
    phases = _bucket_into_phases(ids)
    assert phases[ids[0]] == RoadmapPhase.FOUNDATIONS
    assert phases[ids[1]] == RoadmapPhase.FOUNDATIONS
    assert phases[ids[2]] == RoadmapPhase.CORE
    assert phases[ids[3]] == RoadmapPhase.CORE
    assert phases[ids[4]] == RoadmapPhase.ADVANCED
    assert phases[ids[5]] == RoadmapPhase.ADVANCED
