"""Greek god–themed boons (Hades-style picks on level-up)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Callable, List


@dataclass
class Boon:
    id: str
    god: str
    title: str
    description: str
    rarity: str  # common, rare, epic
    apply_fn: Callable[[Any], None]


def _apply_zeus(game: Any) -> None:
    p = game.player
    p.damage_mult *= 1.15
    p.chain_lightning += 0.12
    p.projectile_size_mult *= 1.05


def _apply_poseidon(game: Any) -> None:
    p = game.player
    p.pierce += 1
    p.projectile_speed_mult *= 0.92
    p.damage_mult *= 1.08


def _apply_hades(game: Any) -> None:
    p = game.player
    p.aura_radius = max(p.aura_radius, 90) + 35
    p.aura_damage += 4


def _apply_athena(game: Any) -> None:
    p = game.player
    p.max_hp += 25
    p.hp = min(p.hp + 25, p.max_hp)
    p.damage_reduction = min(0.45, p.damage_reduction + 0.06)


def _apply_ares(game: Any) -> None:
    p = game.player
    p.damage_mult *= 1.22
    p.fire_rate_mult *= 1.12


def _apply_apollo(game: Any) -> None:
    p = game.player
    p.fire_rate_mult *= 0.82


def _apply_artemis(game: Any) -> None:
    p = game.player
    p.projectile_count += 1


def _apply_hermes(game: Any) -> None:
    p = game.player
    p.speed_mult *= 1.12
    p.magnet_bonus += 40


def _apply_dionysus(game: Any) -> None:
    p = game.player
    p.slow_on_hit = min(0.65, p.slow_on_hit + 0.08)
    p.damage_mult *= 1.05


def _apply_aphrodite(game: Any) -> None:
    p = game.player
    p.enemy_damage_taken_mult *= 1.1


def _apply_hephaestus(game: Any) -> None:
    p = game.player
    p.burn_on_hit += 0.18
    p.damage_mult *= 1.08


def _apply_demeter(game: Any) -> None:
    p = game.player
    p.knockback_mult *= 1.25
    p.max_hp += 10
    p.hp = min(p.hp + 10, p.max_hp)


ALL_BOONS: List[Boon] = [
    Boon(
        "zeus_bolt",
        "Zeus",
        "Skybreaker",
        "Bolts bite harder; lightning may leap to a second foe.",
        "rare",
        _apply_zeus,
    ),
    Boon(
        "poseidon_trident",
        "Poseidon",
        "Depth Piercer",
        "Spears pierce +1 foe; slightly slower but relentless.",
        "common",
        _apply_poseidon,
    ),
    Boon(
        "hades_soul",
        "Hades",
        "River's Edge",
        "A stygian ring damages nearby shades.",
        "rare",
        _apply_hades,
    ),
    Boon(
        "athena_aegis",
        "Athena",
        "Aegis Bulwark",
        "Wisdom hardens flesh: +HP and less pain from hits.",
        "epic",
        _apply_athena,
    ),
    Boon(
        "ares_fury",
        "Ares",
        "Bloodlust",
        "Pure violence: more damage, slightly faster throws.",
        "common",
        _apply_ares,
    ),
    Boon(
        "apollo_sun",
        "Apollo",
        "Solar Cadence",
        "Arrows of light — you loose spears faster.",
        "common",
        _apply_apollo,
    ),
    Boon(
        "artemis_twin",
        "Artemis",
        "Twin Draw",
        "An extra spear splits from each cast.",
        "epic",
        _apply_artemis,
    ),
    Boon(
        "hermes_wing",
        "Hermes",
        "Windstep",
        "Move like a messenger; orbs pull from farther.",
        "common",
        _apply_hermes,
    ),
    Boon(
        "dionysus_wine",
        "Dionysus",
        "Madness Vintage",
        "Struck foes stumble; chaos favors you.",
        "rare",
        _apply_dionysus,
    ),
    Boon(
        "aphrodite_charm",
        "Aphrodite",
        "Softened Hearts",
        "Enemies suffer more from all your harm.",
        "rare",
        _apply_aphrodite,
    ),
    Boon(
        "hephaestus_forge",
        "Hephaestus",
        "Forgefire",
        "Spears may ignite; smith's strength in every throw.",
        "rare",
        _apply_hephaestus,
    ),
    Boon(
        "demeter_reap",
        "Demeter",
        "Autumn Shove",
        "Harvest's push — stronger knockback and vitality.",
        "common",
        _apply_demeter,
    ),
]


def roll_boon_choices(count: int = 3) -> List[Boon]:
    """Weighted by rarity for a Hades-like feel."""
    pool = list(ALL_BOONS)
    weights = []
    for b in pool:
        w = {"common": 4, "rare": 2, "epic": 1}.get(b.rarity, 2)
        weights.append(w)
    choices: List[Boon] = []
    for _ in range(count):
        if not pool:
            break
        pick = random.choices(pool, weights=weights, k=1)[0]
        idx = pool.index(pick)
        pool.pop(idx)
        weights.pop(idx)
        choices.append(pick)
    return choices
