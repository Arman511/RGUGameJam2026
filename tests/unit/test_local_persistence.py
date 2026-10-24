from pathlib import Path

from elemental_keep.local_database import LocalLeaderboardStore

def test_database_initialises_and_persists_runs(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")
    db.submit_run(
        run_id="run-1",
        score=1500,
        survival_time=64.2,
        final_wave=5,
        enemies_defeated=14,
    )
    rows = db.top_scores(limit=5)
    assert rows[0]["score"] == 1500
    assert rows[0]["run_id"] == "run-1"

def test_duplicate_run_ids_are_handled_safely(tmp_path: Path) -> None:
    db = LocalLeaderboardStore(path=tmp_path / "leaderboard.db")
    db.submit_run("run-dup", 10, 5.0, 2, 4)
    db.submit_run("run-dup", 20, 7.0, 3, 5)
    assert db.top_scores(limit=10)[0]["score"] == 20
