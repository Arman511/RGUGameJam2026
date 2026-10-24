def build_wave_sequence(wave_number: int) -> list[str]:
    if wave_number < 1:
        raise ValueError("wave_number must be positive")
    if wave_number % 5 == 0:
        regulars = ["runner"] * max(2, wave_number // 2) + ["brute"] * max(
            2, wave_number // 3
        )
        elites = ["elite_fire", "elite_earth"][: max(1, wave_number // 10)]
        return ["boss", *elites, *regulars]
    if wave_number == 1:
        return ["swarmer", "swarmer", "swarmer"]
    if wave_number == 2:
        return ["swarmer"] * 4 + ["brute"] * 1
    swarmers = max(2, 7 - wave_number)
    runners = 2 + wave_number
    brutes = 1 + wave_number // 2
    wave = ["swarmer"] * swarmers + ["runner"] * runners + ["brute"] * brutes
    if wave_number >= 3:
        elite_types = (
            "elite_fire",
            "elite_water",
            "elite_earth",
            "elite_air",
            "elite_lightning",
        )
        wave.extend(
            [elite_types[(wave_number - 3) % len(elite_types)]] * (1 + wave_number // 4)
        )
    return wave


class Waves:
    def __init__(self):
        self.weather = self.get_weather()
