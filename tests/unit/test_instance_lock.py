from elemental_game.utils.instance_lock import GameInstanceLock


def test_only_one_game_instance_can_hold_the_lock(tmp_path) -> None:
    lock_path = tmp_path / "game.lock"
    first = GameInstanceLock(lock_path)
    second = GameInstanceLock(lock_path)

    assert first.acquire()
    assert not second.acquire()

    first.release()
    first.release()
    assert second.acquire()
    second.release()
