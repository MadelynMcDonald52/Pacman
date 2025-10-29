"""
Mini Pac-Man clone (with portals, ghost delay, and lives/Game Over)
Controls:
  - Arrow keys = move
  - P = pause
  - ESC = quit
  - SPACE = restart after Game Over
Requires: pygame  (pip install pygame)
"""

import pygame
import sys
import random
from collections import deque

# ----- Configuration -----
TILE = 24
ROWS = 21
COLS = 21
SCREEN_W = COLS * TILE
SCREEN_H = ROWS * TILE + 40
FPS = 60

# Colors
BLACK = (0, 0, 0)
NAVY = (10, 10, 40)
YELLOW = (255, 220, 0)
WHITE = (255, 255, 255)
DOT_COLOR = (200, 200, 200)
PELLET_COLOR = (255, 180, 180)
GHOST_COLORS = [(255, 0, 0), (255, 128, 255), (0, 255, 255), (255, 128, 0)]

# Ghost movement delay (higher = slower)
GHOST_STEP_DELAY = 8

# ----- Map -----
MAP = [
"#####################",
"#...................#",
"#.###.###.#.###.###.#",
"#o###.###.#.###.###.#",
"#...................#",
"#.###.#.#####.#.###.#",
"#.....#...#...#.....#",
"#####.### # ###.#####",
"     .#   G   #.     ",
"#####.# ##### #.#####",
"#.........P.........#",
"#.#.###.#####.###.#.#",
"#...#...#...#...#...#",
"#.#.###.#.#.#.###.#.#",
"#o#.....#.#.#.....#.#",
"#.#.#####.#.#####.#.#",
"#...................#",
"#.###.###.#.###.###.#",
"#o..#.....#.....#..o#",
"#...................#",
"#####################",
]
MAP = [row.ljust(COLS)[:COLS] for row in MAP]

total_level = 1
pellet_total = 0
pellet_count = 0

for r, row in enumerate(MAP):
        for c, ch in enumerate(row):
            if ch == ".": pellet_total = pellet_total+1
pellet_count = pellet_total

# ----- Helpers -----
def load_level():
    pellets, power_pellets, walls = set(), set(), set()
    player_pos, ghosts_pos = None, []
    for r, row in enumerate(MAP):
        for c, ch in enumerate(row):
            if ch == "#": walls.add((c, r))
            elif ch == ".": pellets.add((c, r))
            elif ch == "o": power_pellets.add((c, r))
            elif ch == "P": player_pos = (c, r)
            elif ch == "G": ghosts_pos.append((c, r))
    return walls, pellets, power_pellets, player_pos, ghosts_pos


def tile_to_pixel(pos):
    x, y = pos
    return x * TILE + TILE // 2, y * TILE + TILE // 2


def valid_tile(pos, walls):
    x, y = pos
    if y < 0 or y >= ROWS:
        return False
    return (x % COLS, y) not in walls


def neighbors(tile_pos, walls):
    x, y = tile_pos
    results = []
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        nx, ny = (x + dx) % COLS, y + dy
        if valid_tile((nx, ny), walls):
            results.append((nx, ny))
    return results


def bfs(start, target, walls):
    if start == target:
        return [start]
    queue = deque([start])
    prev = {start: None}
    while queue:
        node = queue.popleft()
        for n in neighbors(node, walls):
            if n not in prev:
                prev[n] = node
                if n == target:
                    path = [n]
                    cur = n
                    while prev[cur] is not None:
                        cur = prev[cur]
                        path.append(cur)
                    return list(reversed(path))
                queue.append(n)
    return None


# ----- Player -----
class Player:
    def __init__(self, pos):
        self.tile = pos
        self.dir = (0, 0)
        self.next_dir = (0, 0)
        self.speed = 6
        self.pixel = list(tile_to_pixel(pos))
        self.radius = TILE//2 - 2
        self.lives = 3
        self.level = total_level

    def update(self, walls):
        cx, cy = self.pixel
        tx, ty = tile_to_pixel(self.tile)
        if abs(cx - tx) < 2 and abs(cy - ty) < 2:
            self.pixel[0], self.pixel[1] = tx, ty
            nx_tile = ((self.tile[0] + self.next_dir[0]) % COLS, self.tile[1] + self.next_dir[1])
            if valid_tile(nx_tile, walls):
                self.dir = self.next_dir
            cur_tile = ((self.tile[0] + self.dir[0]) % COLS, self.tile[1] + self.dir[1])
            if not valid_tile(cur_tile, walls):
                self.dir = (0,0)
            self.tile = ((self.tile[0] + self.dir[0]) % COLS, self.tile[1] + self.dir[1]) if self.dir != (0,0) else self.tile

        self.pixel[0] += self.dir[0] * self.speed
        self.pixel[1] += self.dir[1] * self.speed

        if self.pixel[0] < 0:
            self.pixel[0] = SCREEN_W
        elif self.pixel[0] > SCREEN_W:
            self.pixel[0] = 0

        if self.dir == (0,0):
            self.pixel[0], self.pixel[1] = tile_to_pixel(self.tile)

    def set_direction(self, dir_tuple):
        self.next_dir = dir_tuple

    def is_moving(self):
        return self.dir != (0, 0)

    def draw(self, surf):
        pygame.draw.circle(surf, YELLOW, (int(self.pixel[0]), int(self.pixel[1])), self.radius)


# ----- Ghost -----
class Ghost:
    def __init__(self, pos, color):
        self.start_tile = pos
        self.tile = pos
        self.pixel = list(tile_to_pixel(pos))
        self.radius = TILE//2 - 2
        self.color = color
        self.mode = 'chase'
        self.fright_timer = 0

    def set_frightened(self, duration):
        self.mode = 'frightened'
        self.fright_timer = duration

    def update(self, walls, player_tile):
        if self.mode == 'frightened':
            if random.random() < 0.1:
                choices = neighbors(self.tile, walls)
                if choices:
                    self.tile = random.choice(choices)
            self.fright_timer -= 1
            if self.fright_timer <= 0:
                self.mode = 'chase'
        else:
            if random.random() < 0.05:
                path = bfs(self.tile, player_tile, walls)
                if path and len(path) > 1:
                    self.tile = path[1]
            else:
                possible = neighbors(self.tile, walls)
                if possible:
                    possible.sort(key=lambda t: abs(t[0]-player_tile[0])+abs(t[1]-player_tile[1]))
                    self.tile = possible[0]

        self.tile = (self.tile[0] % COLS, self.tile[1])
        self.pixel = list(tile_to_pixel(self.tile))

    def draw(self, surf):
        color = (120,160,255) if self.mode == 'frightened' else self.color
        pygame.draw.circle(surf, color, (int(self.pixel[0]), int(self.pixel[1])), self.radius)

    def reset(self):
        self.tile = self.start_tile
        self.pixel = list(tile_to_pixel(self.start_tile))
        self.mode = 'chase'
        self.fright_timer = 0


# ----- Main -----
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Mini Pac-Man (Portals + Lives + Game Over)")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)
    bigfont = pygame.font.SysFont("Arial", 28, bold=True)

    def new_game():
        walls, pellets, power_pellets, player_start, ghosts_starts = load_level()
        player = Player(player_start)
        ghosts = [Ghost(pos, GHOST_COLORS[i % len(GHOST_COLORS)]) for i, pos in enumerate(ghosts_starts)]
        return walls, pellets, power_pellets, player, ghosts, player_start

    walls, pellets, power_pellets, player, ghosts, player_start = new_game()
    score = 0
    frightened_duration = 50
    paused = False
    game_over = False
    game_win = False
    frame_counter = 0
    player_moved = False

    def draw_map(surface):
        surface.fill(NAVY)
        for r in range(ROWS):
            for c in range(COLS):
                if (c, r) in walls:
                    pygame.draw.rect(surface, BLACK, (c*TILE, r*TILE, TILE, TILE))
                    pygame.draw.rect(surface, (40,40,60), (c*TILE+2, r*TILE+2, TILE-4, TILE-4))
        for p in pellets:
            x, y = tile_to_pixel(p)
            pygame.draw.circle(surface, DOT_COLOR, (x, y), 3)
        for p in power_pellets:
            x, y = tile_to_pixel(p)
            pygame.draw.circle(surface, PELLET_COLOR, (x, y), 6)

    # ---------- Game loop ----------
    while True:
        dt = clock.tick(FPS)
        frame_counter += 1
        global pellet_count
        global total_level

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_p:
                    paused = not paused
                if not game_over and not game_win and not paused:
                    if event.key == pygame.K_LEFT: player.set_direction((-1,0))
                    elif event.key == pygame.K_RIGHT: player.set_direction((1,0))
                    elif event.key == pygame.K_UP: player.set_direction((0,-1))
                    elif event.key == pygame.K_DOWN: player.set_direction((0,1))
                if (game_over or game_win) and event.key == pygame.K_SPACE:
                    walls, pellets, power_pellets, player, ghosts, player_start = new_game()
                    score = 0
                    player_moved = False
                    game_over = False
                    pellet_count = pellet_total
                    game_win = False

        if not paused and not game_over and not game_win:
            player.update(walls)
            if player.is_moving():
                player_moved = True

            # Pellet collection
            if player.tile in pellets:
                pellets.remove(player.tile)
                pellet_count = pellet_count-1
                score += 10
            if player.tile in power_pellets:
                power_pellets.remove(player.tile)
                score += 50
                for g in ghosts:
                    g.set_frightened(frightened_duration)
    
            if pellet_count == 0:
                game_win = True
                total_level = total_level + 1
                player.level = player.level + 1

            # Ghost movement
            if player_moved and frame_counter % GHOST_STEP_DELAY == 0:
                for g in ghosts:
                    g.update(walls, player.tile)

            # Collisions
            for g in ghosts:
                if g.tile == player.tile:
                    if g.mode == 'frightened':
                        score += 200
                        g.reset()
                    else:
                        player.lives -= 1
                        player_moved = False
                        if player.lives <= 0:
                            game_over = True
                        else:
                            # reset to start but keep lives
                            player.tile = player_start
                            player.pixel = list(tile_to_pixel(player_start))
                            player.dir = (0, 0)
                            player.next_dir = (0, 0)
                            for gh in ghosts: gh.reset()

        # ----- Draw everything -----
        draw_map(screen)
        for g in ghosts: g.draw(screen)
        player.draw(screen)

        pygame.draw.rect(screen, (20,20,30), (0, ROWS*TILE, SCREEN_W, 40))
        screen.blit(font.render(f"Score: {score}", True, WHITE), (8, ROWS*TILE + 8))
        screen.blit(font.render(f"Lives: {player.lives}", True, WHITE), (200, ROWS*TILE + 8))
        screen.blit(font.render(f"Level: {player.level}", True, WHITE), (400, ROWS*TILE + 8))

        if paused:
            txt = bigfont.render("PAUSED - press P to resume", True, WHITE)
            screen.blit(txt, (SCREEN_W//2 - txt.get_width()//2, SCREEN_H//2 - 20))

        if game_over:
            txt1 = bigfont.render("GAME OVER", True, WHITE)
            txt2 = font.render("Press SPACE to restart", True, WHITE)
            screen.blit(txt1, (SCREEN_W//2 - txt1.get_width()//2, SCREEN_H//2 - 30))
            screen.blit(txt2, (SCREEN_W//2 - txt2.get_width()//2, SCREEN_H//2 + 10))

        if game_win:
            txt1 = bigfont.render("GAME WIN", True, WHITE)
            txt2 = font.render("Press SPACE to restart", True, WHITE)
            screen.blit(txt1, (SCREEN_W//2 - txt1.get_width()//2, SCREEN_H//2 - 30))
            screen.blit(txt2, (SCREEN_W//2 - txt2.get_width()//2, SCREEN_H//2 + 10))

        pygame.display.flip()


if __name__ == "__main__":
    main()
