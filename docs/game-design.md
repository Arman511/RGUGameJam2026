# Game design

Elemental Keep is a single-player farming survival game where players tend crops, defend a farmhouse, and survive enemy waves.

## Core loop
1. Plant elemental seeds on farm plots during the 60-second preparation phase.
2. Harvest crops when mature to gain elemental resources.
3. Spend five matching crops to build an elemental turret on a soil pad. Each
   side starts with three pads; the market sells four more for 10, 20, 30, and
   40 coins.
4. Survive 30-second enemy waves. Normal enemies attack the farmhouse; bosses
   appear every fifth wave and can destroy elemental turrets.
5. Save the result to the local leaderboard.

At game over, every run is saved locally. Guests enter a leaderboard username;
players can then choose to publish the run to the online leaderboard. Online
publishing requires signing in. The local leaderboard masks rude usernames by
default; clicking a name reveals it.

## Elements
Fire, water, earth, air, ice, and lightning turrets each use their own artwork
and have distinct damage, firing-rate, slowdown, and knockback profiles. Nearby
targets can be acquired in close range, while the directional firing cone covers
the turret's facing side. Press O to show or hide faint turret-range outlines.
Elemental turret upgrades cost increasingly many
crops of the turret's element.

The farmhouse's standard turret is controlled manually from its roof: use
left/right or A/D to aim and Space to fire at targets at any distance. Press E while controlling it to
spend coins on damage and fire-rate upgrades.

Defeated enemies automatically reward a random tier-one seed. The reward amount
is scaled by `ENEMY_SEED_DROP_MULTIPLIER` in `elemental_game.config`.

## Difficulty
Slimes are neutral to elemental attacks. Elemental enemies have elemental
resistances, while elite enemies appear from wave three and increase in number
as waves progress. Fire is strong against air and weak against water; earth is
strong against lightning and weak against water. Other elements follow the
corresponding matchup table in the game code. A 60-second preparation phase
precedes the first wave and follows each 30-second enemy wave; both durations
are configurable in `elemental_game.config`.
