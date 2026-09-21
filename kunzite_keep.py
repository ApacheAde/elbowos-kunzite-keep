#!/usr/bin/env python3
"""Kunzite Keep — neon tower-lite arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "KUNZITE KEEP"
HANDLE = "x.com/ElbowOS"

VOID = (14, 6, 22)
PLUM = (42, 12, 58)
INK = (28, 8, 40)
LILAC = (210, 150, 255)
MAG = (255, 70, 170)
ROSE = (255, 110, 150)
GOLD = (255, 210, 80)
CYAN = (80, 240, 255)
CREAM = (250, 236, 255)
MINT = (120, 255, 190)
CRIM = (255, 60, 90)

LANES = 4
COLS, ROWS = 4, 3
LEFT, RIGHT = 90, W - 90
TOP, GRID_TOP, GRID_BOT = 300, 980, 1480
KEEP_Y = 1620


def lane_x(i: int) -> float:
    return LEFT + (i + 0.5) * (RIGHT - LEFT) / LANES


def cell_xy(c: int, r: int) -> tuple[float, float]:
    cw = (RIGHT - LEFT) / COLS
    ch = (GRID_BOT - GRID_TOP) / ROWS
    return LEFT + (c + 0.5) * cw, GRID_TOP + (r + 0.5) * ch


class Enemy:
    def __init__(self, lane: int, kind: int):
        self.lane = lane
        self.x = lane_x(lane)
        self.y = TOP - 40.0
        self.kind = kind  # 0 grunt, 1 runner, 2 tank
        self.hp = (1, 1, 3)[kind]
        self.spd = (140, 230, 90)[kind]
        self.wob = random.uniform(0, 6.28)
        self.alive = True


class Tower:
    def __init__(self, c: int, r: int):
        self.c, self.r = c, r
        self.x, self.y = cell_xy(c, r)
        self.cool = 0.0
        self.life = 14.0
        self.pulse = 0.0


class Shot:
    def __init__(self, x: float, y: float, lane: int):
        self.x, self.y, self.lane = x, y, lane
        self.alive = True


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 76)
        self.font_md = pygame.font.Font(None, 48)
        self.font_sm = pygame.font.Font(None, 34)
        self.cur_c, self.cur_r = 1, 2
        self.towers: list[Tower] = []
        self.enemies: list[Enemy] = []
        self.shots: list[Shot] = []
        self.sparks: list[list[float]] = []
        self.pops: list[tuple[str, float, float, float]] = []
        self.score = 0
        self.kills = 0
        self.keep = 8
        self.energy = 4.0
        self.wave = 1
        self.spawn_t = 0.4
        self.t = 0.0
        self.plant_cool = 0.0
        self.running = True
        self.screen = None
        if not record:
            self.screen = pygame.display.set_mode((W, H))
            pygame.display.set_caption(TITLE)

    def occupied(self, c: int, r: int) -> bool:
        return any(tw.c == c and tw.r == r for tw in self.towers)

    def plant(self) -> None:
        if self.plant_cool > 0 or self.energy < 1.0:
            return
        if self.occupied(self.cur_c, self.cur_r):
            return
        self.towers.append(Tower(self.cur_c, self.cur_r))
        self.energy -= 1.0
        self.plant_cool = 0.22
        x, y = cell_xy(self.cur_c, self.cur_r)
        for _ in range(12):
            a = random.uniform(0, 6.28)
            self.sparks.append([x, y, math.cos(a) * 280, math.sin(a) * 220, 0.35, *LILAC])

    def burst(self, x: float, y: float, col: tuple[int, int, int], n: int = 14) -> None:
        for _ in range(n):
            a = random.uniform(0, 6.28)
            self.sparks.append([x, y, math.cos(a) * 340, math.sin(a) * 260, 0.4, *col])

    def autoplay(self) -> None:
        threat = [0.0] * LANES
        for e in self.enemies:
            threat[e.lane] += (1.4 if e.kind == 2 else 1.0) * (e.y / H)
        cover = [0] * LANES
        for tw in self.towers:
            cover[tw.c] += 1
        need = max(range(LANES), key=lambda i: threat[i] - cover[i] * 0.7)
        self.cur_c = need
        self.cur_r = 2 if threat[need] > 0.8 else (1 if threat[need] > 0.3 else 0)
        if cover[need] < 2 and self.energy >= 1.0 and not self.occupied(self.cur_c, self.cur_r):
            self.plant()
        elif self.energy >= 2.2 and len(self.towers) < 6:
            for r in (2, 1, 0):
                if not self.occupied(need, r):
                    self.cur_r = r
                    self.plant()
                    break

    def spawn(self) -> None:
        lane = random.randrange(LANES)
        roll = random.random()
        kind = 2 if roll > 0.86 else (1 if roll > 0.62 else 0)
        if self.t > 8 and random.random() < 0.25:
            kind = 2
        self.enemies.append(Enemy(lane, kind))

    def update(self, dt: float) -> None:
        self.t += dt
        self.plant_cool = max(0.0, self.plant_cool - dt)
        self.energy = min(6.0, self.energy + dt * 0.55)
        self.wave = 1 + int(self.t // 6)
        self.spawn_t -= dt
        rate = max(0.32, 0.95 - self.t * 0.03)
        if self.spawn_t <= 0:
            self.spawn()
            if random.random() < 0.28 + min(0.3, self.t * 0.02):
                self.spawn()
            self.spawn_t = rate
        if self.record:
            self.autoplay()
        else:
            keys = pygame.key.get_pressed()
            _ = keys
        for tw in self.towers:
            tw.life -= dt
            tw.cool = max(0.0, tw.cool - dt)
            tw.pulse += dt * 8
            if tw.cool <= 0:
                self.shots.append(Shot(tw.x, tw.y - 28, tw.c))
                tw.cool = 0.38
        self.towers = [tw for tw in self.towers if tw.life > 0]
        for sh in self.shots:
            sh.y -= 920 * dt
            if sh.y < TOP - 30:
                sh.alive = False
            for e in self.enemies:
                if not e.alive or e.lane != sh.lane:
                    continue
                if abs(e.x - sh.x) < 46 and abs(e.y - sh.y) < 36:
                    e.hp -= 1
                    sh.alive = False
                    self.burst(e.x, e.y, CYAN, 8)
                    if e.hp <= 0:
                        e.alive = False
                        pts = (80, 120, 220)[e.kind]
                        self.score += pts
                        self.kills += 1
                        self.energy = min(6.0, self.energy + 0.18)
                        tag = ("POP", "ZIP", "CRACK")[e.kind]
                        self.pops.append((f"{tag} +{pts}", e.x, e.y, 0.7))
                        self.burst(e.x, e.y, GOLD if e.kind == 2 else MAG, 16)
                    break
        self.shots = [s for s in self.shots if s.alive]
        for e in self.enemies:
            if not e.alive:
                continue
            e.wob += dt * 6
            e.y += e.spd * dt
            e.x = lane_x(e.lane) + math.sin(e.wob) * 10
            if e.y >= KEEP_Y - 20:
                e.alive = False
                self.keep -= 1 if e.kind != 2 else 2
                self.burst(e.x, KEEP_Y - 10, CRIM, 18)
                self.pops.append(("BREACH", e.x, KEEP_Y - 80, 0.8))
                if self.keep <= 0:
                    self.keep = 8
                    self.score = max(0, self.score - 150)
                    self.pops.append(("KEEP REFORGED", W * 0.5, 860, 1.1))
        self.enemies = [e for e in self.enemies if e.alive]
        nxt = []
        for sp in self.sparks:
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            sp[4] -= dt
            if sp[4] > 0:
                nxt.append(sp)
        self.sparks = nxt
        self.pops = [(a, x, y - 70 * dt, life - dt) for a, x, y, life in self.pops if life - dt > 0]

    def draw(self, s: pygame.Surface) -> None:
        s.fill(VOID)
        pygame.draw.rect(s, INK, (0, 0, LEFT - 8, H))
        pygame.draw.rect(s, INK, (RIGHT + 8, 0, W - RIGHT, H))
        pygame.draw.rect(s, MAG, (LEFT - 12, 0, 6, H))
        pygame.draw.rect(s, LILAC, (RIGHT + 6, 0, 6, H))
        rng = random.Random(9)
        for i in range(40):
            mx = rng.randint(LEFT, RIGHT)
            my = (rng.randint(0, H) + int(self.t * (18 + i % 20))) % H
            pygame.draw.circle(s, PLUM, (mx, my), 2 + i % 3)
        cw = (RIGHT - LEFT) / LANES
        for i in range(LANES):
            x0 = int(LEFT + i * cw)
            shade = PLUM if i % 2 == 0 else INK
            pygame.draw.rect(s, shade, (x0 + 4, TOP, int(cw) - 8, KEEP_Y - TOP), border_radius=18)
        for r in range(ROWS):
            for c in range(COLS):
                x, y = cell_xy(c, r)
                sel = c == self.cur_c and r == self.cur_r
                col = GOLD if sel else (80, 40, 110)
                pygame.draw.circle(s, col, (int(x), int(y)), 28, 2 if not sel else 4)
        for tw in self.towers:
            rad = 26 + int(4 * math.sin(tw.pulse))
            pygame.draw.circle(s, MAG, (int(tw.x), int(tw.y)), rad)
            pygame.draw.circle(s, LILAC, (int(tw.x), int(tw.y)), rad - 8)
            pygame.draw.circle(s, CREAM, (int(tw.x) - 6, int(tw.y) - 6), 6)
            pygame.draw.rect(s, GOLD, (int(tw.x) - 4, int(tw.y) - 38, 8, 22), border_radius=3)
        for sh in self.shots:
            pygame.draw.circle(s, CYAN, (int(sh.x), int(sh.y)), 9)
            pygame.draw.circle(s, CREAM, (int(sh.x), int(sh.y)), 4)
        kinds = ((ROSE, 16), (MINT, 14), (GOLD, 22))
        for e in self.enemies:
            col, rad = kinds[e.kind]
            pygame.draw.polygon(
                s,
                col,
                [
                    (int(e.x), int(e.y - rad)),
                    (int(e.x + rad), int(e.y + rad * 0.6)),
                    (int(e.x), int(e.y + rad * 0.2)),
                    (int(e.x - rad), int(e.y + rad * 0.6)),
                ],
            )
            pygame.draw.circle(s, CREAM, (int(e.x), int(e.y - 2)), 4)
        pygame.draw.rect(s, PLUM, (LEFT, KEEP_Y, RIGHT - LEFT, 90), border_radius=16)
        pygame.draw.rect(s, MAG, (LEFT, KEEP_Y, RIGHT - LEFT, 90), 3, border_radius=16)
        for i in range(self.keep):
            pygame.draw.rect(s, GOLD if i < self.keep else INK, (LEFT + 20 + i * 48, KEEP_Y + 28, 36, 36), border_radius=6)
        for sp in self.sparks:
            pygame.draw.circle(s, (int(sp[5]), int(sp[6]), int(sp[7])), (int(sp[0]), int(sp[1])), 5)
        title = self.font_lg.render(TITLE, True, LILAC)
        s.blit(title, title.get_rect(center=(W // 2, 64)))
        handle = self.font_sm.render(HANDLE, True, GOLD)
        s.blit(handle, handle.get_rect(center=(W // 2, 118)))
        s.blit(self.font_md.render(f"SCORE  {self.score}", True, CREAM), (108, 156))
        s.blit(self.font_md.render(f"KILLS  {self.kills}   WAVE {self.wave}", True, MAG), (108, 204))
        s.blit(self.font_sm.render(f"ENERGY {self.energy:.1f}   KEEP {self.keep}", True, CYAN), (108, 252))
        for tag, x, y, life in self.pops:
            img = self.font_md.render(tag, True, GOLD)
            s.blit(img, img.get_rect(center=(int(x), int(y))))
        hint = self.font_sm.render("A/D lane   W/S row   SPACE plant crystal", True, (200, 160, 220))
        s.blit(hint, hint.get_rect(center=(W // 2, H - 40)))

    def handle(self, ev) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key in (pygame.K_a, pygame.K_LEFT):
                self.cur_c = max(0, self.cur_c - 1)
            elif ev.key in (pygame.K_d, pygame.K_RIGHT):
                self.cur_c = min(COLS - 1, self.cur_c + 1)
            elif ev.key in (pygame.K_w, pygame.K_UP):
                self.cur_r = max(0, self.cur_r - 1)
            elif ev.key in (pygame.K_s, pygame.K_DOWN):
                self.cur_r = min(ROWS - 1, self.cur_r + 1)
            elif ev.key == pygame.K_SPACE:
                self.plant()
            elif ev.key == pygame.K_r:
                rec = self.record
                self.__init__(rec)

    def play(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            self.screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    if record:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record)
    if record:
        g.record_mp4("/home/workdir/artifacts/kunzite_keep_ElbowOS.mp4")
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
