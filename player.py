import pygame
import os
from settings import (
    PLAYER_DIR, PLAYER_SPEED, PLAYER_MAX_HEALTH, PLAYER_INVULN_TIME,
    PLAYER_ATTACK_RANGE, PLAYER_ATTACK_COOLDOWN, PLAYER_ATTACK_DURATION,
    PLAYER_SCALE, SPRITE_COLS, SPRITE_ROWS, TILE_SIZE,
    COLOR_RED, COLOR_BLACK, COLOR_GRAY
)


class Player:
    def __init__(self, x, y, audio=None):
        self.x = float(x)
        self.y = float(y)
        self.speed = PLAYER_SPEED
        self.health = PLAYER_MAX_HEALTH
        self.max_health = PLAYER_MAX_HEALTH
        self.alive = True
        self.direction = "down"
        self.moving = False
        self.attacking = False
        self.attack_timer = 0
        self.attack_cooldown = PLAYER_ATTACK_COOLDOWN
        self.invulnerable = False
        self.invuln_timer = 0
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 150
        self.audio = audio
        self._prev_moving = False

        self.walk_sprites = self._load_sprites("personaje.png")
        self.attack_sprites = self._load_sprites("personaje2.png")

        self.current_sprite = self.walk_sprites[self.direction][0]
        self.rect = pygame.Rect(0, 0, TILE_SIZE, TILE_SIZE)
        self.rect.center = (int(self.x), int(self.y))

    def _load_sprites(self, filename):
        filepath = os.path.join(PLAYER_DIR, filename)
        sheet = pygame.image.load(filepath).convert_alpha()
        sheet_width = sheet.get_width()
        sheet_height = sheet.get_height()
        frame_width = sheet_width // SPRITE_COLS
        frame_height = sheet_height // SPRITE_ROWS

        self.sprite_size = int(TILE_SIZE * PLAYER_SCALE)

        sprites = {"down": [], "left": [], "right": [], "up": []}
        directions = ["down", "left", "right", "up"]

        for row, direction in enumerate(directions):
            for col in range(SPRITE_COLS):
                frame = sheet.subsurface(
                    (col * frame_width, row * frame_height, frame_width, frame_height)
                )
                scaled = pygame.transform.smoothscale(
                    frame, (self.sprite_size, self.sprite_size)
                )
                sprites[direction].append(scaled)

        return sprites

    def handle_input(self, keys, game_map=None):
        if not self.alive or self.attacking:
            return

        dx, dy = 0, 0

        if keys[pygame.K_w]:
            dy = -self.speed
            self.direction = "up"
        elif keys[pygame.K_s]:
            dy = self.speed
            self.direction = "down"

        if keys[pygame.K_a]:
            dx = -self.speed
            self.direction = "left"
        elif keys[pygame.K_d]:
            dx = self.speed
            self.direction = "right"

        self.moving = dx != 0 or dy != 0

        if dx != 0:
            new_rect = self.rect.copy()
            new_rect.x += int(dx)
            if not game_map or not game_map.check_collision(new_rect):
                self.rect.x = new_rect.x

        if dy != 0:
            new_rect = self.rect.copy()
            new_rect.y += int(dy)
            if not game_map or not game_map.check_collision(new_rect):
                self.rect.y = new_rect.y

        self.x = float(self.rect.centerx)
        self.y = float(self.rect.centery)

    def attack(self):
        if not self.alive or self.attacking:
            return None

        now = pygame.time.get_ticks()
        if now - self.attack_timer < self.attack_cooldown:
            return None

        self.attacking = True
        self.attack_timer = now
        self.anim_frame = 0
        self.moving = False
        if self.audio:
            self.audio.play_sfx("sword")

        attack_rect = self.rect.copy()
        if self.direction == "up":
            attack_rect.bottom = self.rect.top
            attack_rect.y -= PLAYER_ATTACK_RANGE - self.rect.height
            attack_rect.height = PLAYER_ATTACK_RANGE
        elif self.direction == "down":
            attack_rect.top = self.rect.bottom
            attack_rect.height = PLAYER_ATTACK_RANGE
        elif self.direction == "left":
            attack_rect.right = self.rect.left
            attack_rect.x -= PLAYER_ATTACK_RANGE - self.rect.width
            attack_rect.width = PLAYER_ATTACK_RANGE
        elif self.direction == "right":
            attack_rect.left = self.rect.right
            attack_rect.width = PLAYER_ATTACK_RANGE

        return attack_rect

    def take_damage(self):
        if self.invulnerable or not self.alive:
            return False

        self.health -= 1
        self.invulnerable = True
        self.invuln_timer = pygame.time.get_ticks()

        if self.health <= 0:
            self.alive = False
            if self.audio:
                self.audio.play_sfx("death")
            return True

        if self.audio:
            self.audio.play_sfx("hit")
        return False

    def update(self, dt):
        now = pygame.time.get_ticks()

        was_moving = self._prev_moving
        self._prev_moving = self.moving
        if self.audio:
            if self.moving and not was_moving:
                self.audio.play_sfx("footsteps", loops=-1)
            elif not self.moving and was_moving:
                self.audio.stop_sfx("footsteps")

        if self.attacking and now - self.attack_timer >= PLAYER_ATTACK_DURATION:
            self.attacking = False

        if self.invulnerable and now - self.invuln_timer >= PLAYER_INVULN_TIME:
            self.invulnerable = False

        if self.moving and not self.attacking:
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                frames = self.walk_sprites[self.direction]
                self.anim_frame = (self.anim_frame + 1) % len(frames)
        else:
            self.anim_frame = 0
            self.anim_timer = 0

        if self.attacking:
            frames = self.attack_sprites[self.direction]
            self.current_sprite = frames[self.anim_frame % len(frames)]
        else:
            self.current_sprite = self.walk_sprites[self.direction][self.anim_frame]

    def draw(self, surface, camera_x=0, camera_y=0):
        if self.invulnerable:
            if (pygame.time.get_ticks() // 100) % 2 == 0:
                return

        offset = (self.sprite_size - TILE_SIZE) // 2
        draw_x = self.rect.x - camera_x - offset
        draw_y = self.rect.y - camera_y - offset
        surface.blit(self.current_sprite, (draw_x, draw_y))

    def draw_hearts(self, surface):
        heart_size = 24
        padding = 8
        for i in range(self.max_health):
            x = 20 + i * (heart_size + padding)
            y = 20
            if i < self.health:
                self._draw_heart(surface, x, y, heart_size, COLOR_RED)
            else:
                self._draw_heart(surface, x, y, heart_size, COLOR_GRAY)

    def _draw_heart(self, surface, x, y, size, color):
        points = [
            (x + size // 2, y + size // 4),
            (x + size // 4, y),
            (x, y + size // 4),
            (x, y + size // 2),
            (x + size // 2, y + size),
            (x + size, y + size // 2),
            (x + size, y + size // 4),
            (x + size * 3 // 4, y),
            (x + size // 2, y + size // 4),
        ]
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, COLOR_BLACK, points, 1)
