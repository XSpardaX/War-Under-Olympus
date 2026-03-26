"""Player, enemies, projectiles, and XP orbs."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame

from constants import (
    COLOR_ENEMY,
    COLOR_PLAYER,
    COLOR_PROJECTILE,
    COLOR_XP,
    ENEMY_BASE_HP,
    ENEMY_BASE_SPEED,
    FIRE_RATE_BASE,
    MAGNET_BASE,
    PICKUP_RADIUS,
    PLAYER_BASE_HP,
    PLAYER_BASE_SPEED,
    PLAYER_HP_PER_LEVEL,
    PLAYER_RADIUS,
    PROJECTILE_DAMAGE_BASE,
    PROJECTILE_SPEED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@dataclass
class Player:
    x: float
    y: float
    name: str
    hp: float = PLAYER_BASE_HP
    max_hp: float = PLAYER_BASE_HP
    level: int = 1
    xp: int = 0
    xp_to_next: int = 50
    fire_cooldown: float = 0.0

    # Combat / boon stats
    damage_mult: float = 1.0
    fire_rate_mult: float = 1.0
    speed_mult: float = 1.0
    projectile_count: int = 1
    pierce: int = 0
    chain_lightning: float = 0.0
    aura_radius: float = 0.0
    aura_damage: float = 0.0
    damage_reduction: float = 0.0
    slow_on_hit: float = 0.0
    enemy_damage_taken_mult: float = 1.0
    burn_on_hit: float = 0.0
    knockback_mult: float = 1.0
    magnet_bonus: float = 0.0
    projectile_speed_mult: float = 1.0
    projectile_size_mult: float = 1.0

    facing_angle: float = 0.0

    def speed(self) -> float:
        return PLAYER_BASE_SPEED * self.speed_mult

    def radius(self) -> float:
        return PLAYER_RADIUS

    def magnet_range(self) -> float:
        return MAGNET_BASE + self.magnet_bonus

    def take_damage(self, amount: float) -> None:
        mitigated = amount * (1.0 - self.damage_reduction)
        self.hp -= mitigated

    def add_xp(self, n: int) -> bool:
        self.xp += n
        leveled = False
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.max_hp += PLAYER_HP_PER_LEVEL
            self.hp = min(self.hp + PLAYER_HP_PER_LEVEL, self.max_hp)
            self.xp_to_next = int(self.xp_to_next * 1.18 + 8)
            leveled = True
        return leveled


@dataclass
class Enemy:
    x: float
    y: float
    hp: float
    max_hp: float
    speed: float
    radius: float = 16.0
    slow_mult: float = 1.0
    burn_timer: float = 0.0
    burn_dps: float = 0.0
    kind: str = "shade"

    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class Projectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    pierce_left: int
    radius: float = 8.0
    chain_chance: float = 0.0
    burn_apply: float = 0.0
    slow_apply: float = 0.0
    knockback: float = 1.0


@dataclass
class XpOrb:
    x: float
    y: float
    value: int
    vx: float = 0.0
    vy: float = 0.0


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: Tuple[int, int, int]
    life: float = 0.9
    vy: float = -40.0


def spawn_enemy_wave(difficulty: float) -> Enemy:
    side = random.randint(0, 3)
    margin = 40
    if side == 0:
        x, y = random.uniform(margin, SCREEN_WIDTH - margin), -margin
    elif side == 1:
        x, y = SCREEN_WIDTH + margin, random.uniform(margin, SCREEN_HEIGHT - margin)
    elif side == 2:
        x, y = random.uniform(margin, SCREEN_WIDTH - margin), SCREEN_HEIGHT + margin
    else:
        x, y = -margin, random.uniform(margin, SCREEN_HEIGHT - margin)

    tier = min(5, int(difficulty))
    hp = ENEMY_BASE_HP * (1.0 + 0.22 * difficulty)
    spd = ENEMY_BASE_SPEED * (1.0 + 0.04 * min(difficulty, 12))
    r = 14 + min(tier, 4) * 1.5
    kinds = ["shade", "hoplite", "fury"]
    k = random.choices(kinds, weights=[5, 3, 1 + tier], k=1)[0]
    return Enemy(x=x, y=y, hp=hp, max_hp=hp, speed=spd, radius=r, kind=k)


def update_enemy(e: Enemy, dt: float, px: float, py: float) -> None:
    dx, dy = px - e.x, py - e.y
    dist = math.hypot(dx, dy) or 1.0
    sm = e.slow_mult
    step = e.speed * sm * dt / dist
    e.x += dx * step
    e.y += dy * step
    e.slow_mult = _clamp(e.slow_mult + dt * 0.35, 0.35, 1.0)
    if e.burn_timer > 0:
        e.burn_timer -= dt
        e.hp -= e.burn_dps * dt
        if e.burn_timer <= 0:
            e.burn_dps = 0.0


def draw_player(surface: pygame.Surface, p: Player) -> None:
    cx, cy = int(p.x), int(p.y)
    r = int(p.radius())
    pygame.draw.circle(surface, (60, 45, 30), (cx, cy), r + 3)
    pygame.draw.circle(surface, COLOR_PLAYER, (cx, cy), r)
    pygame.draw.circle(surface, (220, 200, 160), (cx, cy), r - 6)
    # Corinthian hint (crest)
    hx = cx + int(math.cos(p.facing_angle) * (r + 6))
    hy = cy + int(math.sin(p.facing_angle) * (r + 6))
    pygame.draw.line(surface, (140, 120, 90), (cx, cy), (hx, hy), 4)


def draw_enemy(surface: pygame.Surface, e: Enemy) -> None:
    cx, cy = int(e.x), int(e.y)
    rr = int(e.radius)
    if e.kind == "hoplite":
        pygame.draw.circle(surface, (90, 85, 110), (cx, cy), rr + 2)
        pygame.draw.circle(surface, (130, 120, 150), (cx, cy), rr)
        pygame.draw.circle(surface, (200, 200, 210), (cx, cy), 5)
    elif e.kind == "fury":
        pygame.draw.circle(surface, (160, 40, 60), (cx, cy), rr + 3)
        pygame.draw.circle(surface, COLOR_ENEMY, (cx, cy), rr)
    else:
        pygame.draw.circle(surface, (40, 35, 55), (cx, cy), rr + 2)
        pygame.draw.circle(surface, COLOR_ENEMY, (cx, cy), rr)


def draw_projectile(surface: pygame.Surface, pr: Projectile) -> None:
    pygame.draw.circle(
        surface,
        COLOR_PROJECTILE,
        (int(pr.x), int(pr.y)),
        max(4, int(pr.radius)),
    )


def draw_xp_orb(surface: pygame.Surface, o: XpOrb) -> None:
    pygame.draw.circle(surface, COLOR_XP, (int(o.x), int(o.y)), PICKUP_RADIUS)
    pygame.draw.circle(surface, (255, 255, 255), (int(o.x), int(o.y)), 4)
