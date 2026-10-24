from __future__ import annotations

def build_wave_sequence(wave_number: int) -> list[str]:
    if wave_number <= 1:
        return ["swarmer", "swarmer", "swarmer"]
    if wave_number <= 3:
        return ["swarmer"] * 4 + ["brute"] * 1
    if wave_number <= 6:
        return ["swarmer"] * 3 + ["runner"] * 3 + ["brute"] * 2
    if wave_number <= 9:
        return ["runner"] * 5 + ["brute"] * 2 + ["swarmer"] * 3
    return ["boss"] + ["runner"] * 2 + ["brute"] * 3 + ["swarmer"] * 5
