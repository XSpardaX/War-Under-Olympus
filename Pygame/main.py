"""
Spartan Survivors — Greek-themed auto-attacker at 1080p (Vampire Survivors–style).
Run: pip install -r requirements.txt && python main.py
"""

from __future__ import annotations

import math
import random
import sys
from typing import List, Optional, Tuple

import pygame

from boons import Boon, roll_boon_choices
from constants import (
    COLOR_BG,
    COLOR_UI_GOLD,
    COLOR_UI_TEXT,
    DIFFICULTY_RAMP_SECONDS,
    ENEMY_SPAWN_MIN,
    ENEMY_SPAWN_START,
    FIRE_RATE_BASE,
    FPS,
    PROJECTILE_DAMAGE_BASE,
    PROJECTILE_SPEED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    XP_PER_LEVEL_BASE,
)
from entities import (
    Enemy,
    FloatingText,
    Player,
    Projectile,
    XpOrb,
    draw_enemy,
    draw_player,
    draw_projectile,
    draw_xp_orb,
    spawn_enemy_wave,
    update_enemy,
)

SPARTAN_NAMES = [
    "Leonidas",
    "Dienekes",
    "Brasidas",
    "Chilon",
    "Pausanias",
    "Gylippus",
    "Callicratidas",
    "Lysander",
    "Aristodemus",
    "Eurytus",
]


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Spartan Survivors — Ἀγών τῶν Θεῶν")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 42)
        self.font_small = pygame.font.Font(None, 30)
        self.font_title = pygame.font.Font(None, 56)
        self.font_boon = pygame.font.Font(None, 34)

        self.player: Player
        self.enemies: List[Enemy]
        self.projectiles: List[Projectile]
        self.orbs: List[XpOrb]
        self.float_texts: List[FloatingText]

        self.spawn_acc: float = 0.0
        self.spawn_interval: float = ENEMY_SPAWN_START
        self.elapsed: float = 0.0
        self.state: str = "playing"
        self.boon_choices: List[Boon] = []
        self.game_over: bool = False

        self.reset()

    def reset(self) -> None:
        name = random.choice(SPARTAN_NAMES)
        self.player = Player(float(SCREEN_WIDTH // 2), float(SCREEN_HEIGHT // 2), name)
        self.player.xp_to_next = XP_PER_LEVEL_BASE
        self.enemies = []
        self.projectiles = []
        self.orbs = []
        self.float_texts = []
        self.spawn_acc = 0.0
        self.spawn_interval = ENEMY_SPAWN_START
        self.elapsed = 0.0
        self.state = "playing"
        self.boon_choices = []
        self.game_over = False

    def difficulty(self) -> float:
        return 1.0 + self.elapsed / DIFFICULTY_RAMP_SECONDS

    def nearest_enemy(self, x: float, y: float) -> Optional[Enemy]:
        best: Optional[Enemy] = None
        best_d = 1e18
        for e in self.enemies:
            if not e.alive():
                continue
            d = (e.x - x) ** 2 + (e.y - y) ** 2
            if d < best_d:
                best_d = d
                best = e
        return best

    def fire_projectiles(self) -> None:
        p = self.player
        target = self.nearest_enemy(p.x, p.y)
        if target:
            ang = math.atan2(target.y - p.y, target.x - p.x)
            p.facing_angle = ang
        else:
            ang = p.facing_angle + 0.08

        base_dmg = PROJECTILE_DAMAGE_BASE * p.damage_mult
        spd = PROJECTILE_SPEED * p.projectile_speed_mult
        pr = 7 * p.projectile_size_mult
        count = max(1, p.projectile_count)
        spread = 0.18 if count > 1 else 0.0
        for i in range(count):
            a = ang + (i - (count - 1) / 2) * spread
            vx, vy = math.cos(a) * spd, math.sin(a) * spd
            self.projectiles.append(
                Projectile(
                    x=p.x + math.cos(a) * 24,
                    y=p.y + math.sin(a) * 24,
                    vx=vx,
                    vy=vy,
                    damage=base_dmg,
                    pierce_left=p.pierce,
                    radius=pr,
                    chain_chance=p.chain_lightning,
                    burn_apply=p.burn_on_hit,
                    slow_apply=p.slow_on_hit,
                    knockback=120 * p.knockback_mult,
                )
            )

    def apply_aura(self, dt: float) -> None:
        p = self.player
        if p.aura_radius <= 0 or p.aura_damage <= 0:
            return
        r2 = p.aura_radius * p.aura_radius
        dps = p.aura_damage * p.enemy_damage_taken_mult
        for e in list(self.enemies):
            if not e.alive():
                continue
            dx, dy = e.x - p.x, e.y - p.y
            if dx * dx + dy * dy <= r2:
                e.hp -= dps * dt
                if e.hp <= 0:
                    self.on_enemy_death(e)

    def on_enemy_death(self, e: Enemy) -> None:
        if e not in self.enemies:
            return
        self.enemies.remove(e)
        tier = 1 + int(self.difficulty() * 0.15)
        val = random.randint(2, 4) + tier
        self.orbs.append(XpOrb(e.x, e.y, val))
        if random.random() < 0.06:
            self.float_texts.append(
                FloatingText(e.x, e.y, "+νίκη!", COLOR_UI_GOLD)
            )

    def chain_hit(
        self, origin: Enemy, damage: float, pr: Projectile, skip: Optional[Enemy] = None
    ) -> None:
        if pr.chain_chance <= 0 or random.random() > pr.chain_chance:
            return
        r_chain = 140.0
        r2 = r_chain * r_chain
        candidates = [
            x
            for x in self.enemies
            if x is not origin and x is not skip and x.alive()
            and (x.x - origin.x) ** 2 + (x.y - origin.y) ** 2 <= r2
        ]
        if not candidates:
            return
        t = min(candidates, key=lambda z: (z.x - origin.x) ** 2 + (z.y - origin.y) ** 2)
        t.hp -= damage * 0.55 * self.player.enemy_damage_taken_mult
        self.float_texts.append(
            FloatingText(t.x, t.y - 20, "⚡", (200, 220, 255))
        )
        if t.hp <= 0:
            self.on_enemy_death(t)

    def resolve_projectile_hits(self, dt: float) -> None:
        to_remove: List[Projectile] = []
        for pr in self.projectiles:
            pr.x += pr.vx * dt
            pr.y += pr.vy * dt
            if (
                pr.x < -80
                or pr.y < -80
                or pr.x > SCREEN_WIDTH + 80
                or pr.y > SCREEN_HEIGHT + 80
            ):
                to_remove.append(pr)
                continue

            for e in list(self.enemies):
                if not e.alive():
                    continue
                dx, dy = e.x - pr.x, e.y - pr.y
                if dx * dx + dy * dy <= (e.radius + pr.radius) ** 2:
                    dmg = pr.damage * self.player.enemy_damage_taken_mult
                    e.hp -= dmg
                    if pr.slow_apply > 0:
                        e.slow_mult = min(e.slow_mult, 1.0 - pr.slow_apply * 0.5)
                    if pr.burn_apply > 0 and random.random() < pr.burn_apply:
                        e.burn_timer = max(e.burn_timer, 2.0)
                        e.burn_dps = max(e.burn_dps, pr.damage * 0.35)
                    inv = 1.0 / (math.hypot(pr.vx, pr.vy) or 1.0)
                    kx = pr.vx * inv * pr.knockback * dt
                    ky = pr.vy * inv * pr.knockback * dt
                    e.x += kx
                    e.y += ky

                    self.chain_hit(e, pr.damage, pr)

                    if pr.pierce_left > 0:
                        pr.pierce_left -= 1
                    else:
                        to_remove.append(pr)

                    if e.hp <= 0:
                        self.on_enemy_death(e)
                    break

        for pr in to_remove:
            if pr in self.projectiles:
                self.projectiles.remove(pr)

    def update_orbs(self, dt: float) -> None:
        p = self.player
        mag = p.magnet_range()
        for o in self.orbs:
            dx, dy = p.x - o.x, p.y - o.y
            d = math.hypot(dx, dy) or 1.0
            if d < mag:
                pull = min(520.0, (mag - d) * 3.5)
                o.vx += (dx / d) * pull * dt
                o.vy += (dy / d) * pull * dt
            o.x += o.vx * dt
            o.y += o.vy * dt
            o.vx *= 0.92
            o.vy *= 0.92

        collect: List[XpOrb] = []
        for o in self.orbs:
            if math.hypot(o.x - p.x, o.y - p.y) < p.radius() + 14:
                collect.append(o)
        for o in collect:
            self.orbs.remove(o)
            if p.add_xp(o.value):
                self.state = "boon"
                self.boon_choices = roll_boon_choices(3)

    def update_enemies(self, dt: float) -> None:
        p = self.player
        for e in list(self.enemies):
            if not e.alive():
                continue
            update_enemy(e, dt, p.x, p.y)
            dx, dy = p.x - e.x, p.y - e.y
            if dx * dx + dy * dy <= (e.radius + p.radius()) ** 2:
                p.take_damage(18 * dt * (1.0 + self.difficulty() * 0.05))
                if p.hp <= 0:
                    self.game_over = True
                    self.state = "dead"

    def spawn_logic(self, dt: float) -> None:
        self.spawn_acc += dt
        diff = self.difficulty()
        self.spawn_interval = max(
            ENEMY_SPAWN_MIN, ENEMY_SPAWN_START - 0.022 * self.elapsed
        )
        while self.spawn_acc >= self.spawn_interval:
            self.spawn_acc -= self.spawn_interval
            self.enemies.append(spawn_enemy_wave(diff))
            if diff > 2.5 and random.random() < 0.25:
                self.enemies.append(spawn_enemy_wave(diff))

    def update_combat_timers(self, dt: float) -> None:
        p = self.player
        p.fire_cooldown -= dt
        interval = FIRE_RATE_BASE * p.fire_rate_mult
        if p.fire_cooldown <= 0:
            self.fire_projectiles()
            p.fire_cooldown += interval

    def update_float_texts(self, dt: float) -> None:
        for ft in list(self.float_texts):
            ft.life -= dt
            ft.y += ft.vy * dt
            if ft.life <= 0:
                self.float_texts.remove(ft)

    def tick(self, dt: float) -> None:
        if self.state == "boon" or self.game_over:
            return
        self.elapsed += dt
        self.update_combat_timers(dt)
        self.resolve_projectile_hits(dt)
        self.apply_aura(dt)
        self.update_enemies(dt)
        self.update_orbs(dt)
        self.spawn_logic(dt)
        self.update_float_texts(dt)

    def move_player(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        if self.state != "playing":
            return
        p = self.player
        dx = dy = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        if dx or dy:
            inv = 1.0 / math.hypot(dx, dy)
            dx *= inv
            dy *= inv
        sp = p.speed()
        p.x = max(p.radius(), min(SCREEN_WIDTH - p.radius(), p.x + dx * sp * dt))
        p.y = max(p.radius(), min(SCREEN_HEIGHT - p.radius(), p.y + dy * sp * dt))

    def draw_background(self) -> None:
        s = self.screen
        s.fill(COLOR_BG)
        # Simple Greek floor / column motif
        for i in range(0, SCREEN_WIDTH, 120):
            pygame.draw.line(s, (30, 36, 55), (i, 0), (i, SCREEN_HEIGHT), 1)
        for j in range(0, SCREEN_HEIGHT, 120):
            pygame.draw.line(s, (28, 34, 52), (0, j), (SCREEN_WIDTH, j), 1)
        for cx in range(160, SCREEN_WIDTH, 380):
            pygame.draw.rect(s, (35, 40, 58), (cx, 80, 24, SCREEN_HEIGHT - 160))
            pygame.draw.rect(s, (50, 55, 75), (cx + 4, 80, 16, SCREEN_HEIGHT - 160))

    def draw_hud(self) -> None:
        p = self.player
        bar_w = 420
        bar_x = 40
        bar_y = 28
        # HP
        pygame.draw.rect(self.screen, (40, 40, 50), (bar_x, bar_y, bar_w, 22))
        hp_w = int(bar_w * max(0, min(1, p.hp / p.max_hp)))
        pygame.draw.rect(self.screen, (160, 45, 55), (bar_x, bar_y, hp_w, 22))
        t = self.font_small.render(f"{p.name}  •  HP {int(p.hp)}/{int(p.max_hp)}", True, COLOR_UI_TEXT)
        self.screen.blit(t, (bar_x + 8, bar_y - 2))

        # XP
        y2 = bar_y + 36
        pygame.draw.rect(self.screen, (40, 40, 50), (bar_x, y2, bar_w, 16))
        xp_w = int(bar_w * (p.xp / max(1, p.xp_to_next)))
        pygame.draw.rect(self.screen, (70, 140, 210), (bar_x, y2, xp_w, 16))
        tx = self.font_small.render(
            f"Level {p.level}  —  χάλκος (XP) {p.xp}/{p.xp_to_next}", True, COLOR_UI_TEXT
        )
        self.screen.blit(tx, (bar_x + 8, y2 - 22))

        time_m = int(self.elapsed // 60)
        time_s = int(self.elapsed % 60)
        tr = self.font_small.render(
            f"Time {time_m:02d}:{time_s:02d}  •  Wave strength ×{self.difficulty():.2f}",
            True,
            COLOR_UI_GOLD,
        )
        self.screen.blit(tr, (SCREEN_WIDTH - tr.get_width() - 40, bar_y))

    def draw_boon_overlay(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 12, 22, 210))
        self.screen.blit(overlay, (0, 0))

        title = self.font_title.render("Οἱ θεοὶ offer their favor — choose one boon", True, COLOR_UI_GOLD)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 120))

        cards: List[Tuple[pygame.Rect, Boon]] = []
        cw, ch = 520, 220
        gap = 40
        total_w = 3 * cw + 2 * gap
        start_x = (SCREEN_WIDTH - total_w) // 2
        y = 280

        colors = {"common": (90, 100, 130), "rare": (80, 90, 160), "epic": (120, 70, 140)}
        for i, boon in enumerate(self.boon_choices):
            rect = pygame.Rect(start_x + i * (cw + gap), y, cw, ch)
            cards.append((rect, boon))
            col = colors.get(boon.rarity, (80, 80, 100))
            pygame.draw.rect(self.screen, col, rect, border_radius=12)
            pygame.draw.rect(self.screen, COLOR_UI_GOLD, rect, 3, border_radius=12)

            key_lbl = self.font.render(f"[{i + 1}]", True, (255, 255, 255))
            self.screen.blit(key_lbl, (rect.x + 16, rect.y + 16))

            god = self.font_boon.render(boon.god.upper(), True, COLOR_UI_GOLD)
            self.screen.blit(god, (rect.x + 70, rect.y + 12))

            bt = self.font_small.render(boon.title, True, COLOR_UI_TEXT)
            self.screen.blit(bt, (rect.x + 20, rect.y + 56))

            desc_words = boon.description.split()
            lines: List[str] = []
            cur = ""
            for w in desc_words:
                test = (cur + " " + w).strip()
                if self.font_small.size(test)[0] > cw - 40:
                    lines.append(cur)
                    cur = w
                else:
                    cur = test
            if cur:
                lines.append(cur)
            for li, line in enumerate(lines[:4]):
                surf = self.font_small.render(line, True, (200, 198, 215))
                self.screen.blit(surf, (rect.x + 20, rect.y + 96 + li * 28))

            rarity = self.font_small.render(boon.rarity.upper(), True, (180, 175, 200))
            self.screen.blit(rarity, (rect.x + cw - rarity.get_width() - 16, rect.y + ch - 36))

        hint = self.font_small.render("Press 1, 2, or 3  •  Esc to quit", True, (150, 150, 170))
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 100))

    def draw_game_over(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 8, 14, 230))
        self.screen.blit(overlay, (0, 0))
        t1 = self.font_title.render("The shades claimed you…", True, (200, 80, 80))
        t2 = self.font.render(
            f"{self.player.name} survived {int(self.elapsed)}s  •  Level {self.player.level}",
            True,
            COLOR_UI_TEXT,
        )
        t3 = self.font_small.render("R to restart  •  Esc to quit", True, COLOR_UI_GOLD)
        self.screen.blit(t1, ((SCREEN_WIDTH - t1.get_width()) // 2, SCREEN_HEIGHT // 2 - 80))
        self.screen.blit(t2, ((SCREEN_WIDTH - t2.get_width()) // 2, SCREEN_HEIGHT // 2 - 10))
        self.screen.blit(t3, ((SCREEN_WIDTH - t3.get_width()) // 2, SCREEN_HEIGHT // 2 + 50))

    def choose_boon(self, index: int) -> None:
        if self.state != "boon" or index < 0 or index >= len(self.boon_choices):
            return
        b = self.boon_choices[index]
        b.apply_fn(self)
        self.boon_choices = []
        self.state = "playing"

    def draw_world(self) -> None:
        p = self.player
        if p.aura_radius > 0:
            surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(
                surf,
                (80, 40, 120, 45),
                (int(p.x), int(p.y)),
                int(p.aura_radius),
            )
            self.screen.blit(surf, (0, 0))

        for e in self.enemies:
            if e.alive():
                draw_enemy(self.screen, e)
        for pr in self.projectiles:
            draw_projectile(self.screen, pr)
        for o in self.orbs:
            draw_xp_orb(self.screen, o)
        draw_player(self.screen, p)

        for ft in self.float_texts:
            alpha = max(0, min(255, int(ft.life * 280)))
            col = (*ft.color[:3], alpha) if len(ft.color) == 3 else ft.color
            ts = self.font_small.render(ft.text, True, ft.color[:3])
            ts.set_alpha(alpha)
            self.screen.blit(ts, (int(ft.x - ts.get_width() // 2), int(ft.y)))

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)
                    if self.state == "boon":
                        if event.key in (pygame.K_1, pygame.K_KP1):
                            self.choose_boon(0)
                        elif event.key in (pygame.K_2, pygame.K_KP2):
                            self.choose_boon(1)
                        elif event.key in (pygame.K_3, pygame.K_KP3):
                            self.choose_boon(2)
                    if self.game_over and event.key == pygame.K_r:
                        self.reset()

            keys = pygame.key.get_pressed()
            self.move_player(dt, keys)
            self.tick(dt)

            self.draw_background()
            self.draw_world()
            self.draw_hud()
            if self.state == "boon":
                self.draw_boon_overlay()
            if self.game_over:
                self.draw_game_over()

            pygame.display.flip()


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
