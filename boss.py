import pygame
import math
import os
import random
from settings import (
    BOSS_DIR, BOSS_SPEED, BOSS_HEALTH, BOSS_DAMAGE, BOSS_SCALE,
    BOSS_ATTACK_RATE, BOSS_SPECIAL_ATTACK_RATE, BOSS_SPECIAL_DAMAGE,
    BOSS_SPECIAL_RANGE, TILE_SIZE, COLOR_RED, COLOR_BLACK, COLOR_GREEN,
    COLOR_ORANGE, COLOR_DARK_RED, COLOR_WHITE
)


class BossProjectile:
    def __init__(self, x, y, target_x, target_y, damage):
        self.x = float(x)
        self.y = float(y)
        self.damage = damage
        self.speed = 3.0
        self.alive = True
        self.radius = 6

        dx = target_x - x
        dy = target_y - y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            self.vx = (dx / dist) * self.speed
            self.vy = (dy / dist) * self.speed
        else:
            self.vx = 0
            self.vy = self.speed

        self.rect = pygame.Rect(int(self.x) - self.radius, int(self.y) - self.radius,
                                 self.radius * 2, self.radius * 2)

    def update(self, game_map):
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))

        if game_map.check_collision(self.rect):
            self.alive = False

    def draw(self, surface, camera_x=0, camera_y=0):
        draw_x = int(self.x) - camera_x
        draw_y = int(self.y) - camera_y
        pygame.draw.circle(surface, COLOR_ORANGE, (draw_x, draw_y), self.radius)
        pygame.draw.circle(surface, COLOR_DARK_RED, (draw_x, draw_y), self.radius, 2)


class Boss:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.speed = BOSS_SPEED
        self.health = BOSS_HEALTH
        self.max_health = BOSS_HEALTH
        self.damage = BOSS_DAMAGE
        self.alive = True
        self.active = False
        self.unlocked = False
        self.attack_cooldown = 0
        self.attack_rate = BOSS_ATTACK_RATE
        self.special_cooldown = 0
        self.special_rate = BOSS_SPECIAL_ATTACK_RATE
        self.projectiles = []
        self.knockback_timer = 0

        self.sprite = self._load_sprite()
        self.rect = self.sprite.get_rect()
        self.rect.center = (int(self.x), int(self.y))

    def _load_sprite(self):
        filepath = os.path.join(BOSS_DIR, "boss.png")
        sheet = pygame.image.load(filepath).convert_alpha()
        sheet_width = sheet.get_width()
        sheet_height = sheet.get_height()

        frame_width = sheet_width // 3
        frame_height = sheet_height // 4
        sprite = sheet.subsurface((0, 0, frame_width, frame_height))

        scaled_size = int(TILE_SIZE * BOSS_SCALE)
        return pygame.transform.scale(sprite, (scaled_size, scaled_size))

    def unlock(self):
        self.unlocked = True
        self.active = True

    def update(self, player, game_map, dt):
        if not self.alive or not self.active:
            return

        now = pygame.time.get_ticks()

        if self.knockback_timer > 0 and now - self.knockback_timer < 200:
            return

        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            dx /= distance
            dy /= distance

            new_x = self.x + dx * self.speed
            new_y = self.y + dy * self.speed

            boss_w = self.rect.width
            boss_h = self.rect.height

            test_rect_x = pygame.Rect(
                int(new_x) - boss_w // 2,
                int(self.y) - boss_h // 2,
                boss_w, boss_h
            )
            test_rect_y = pygame.Rect(
                int(self.x) - boss_w // 2,
                int(new_y) - boss_h // 2,
                boss_w, boss_h
            )

            if not game_map.check_collision(test_rect_x):
                self.x = new_x
            if not game_map.check_collision(test_rect_y):
                self.y = new_y

        self.rect.center = (int(self.x), int(self.y))

        for proj in self.projectiles[:]:
            proj.update(game_map)
            if not proj.alive:
                self.projectiles.remove(proj)
            elif proj.rect.colliderect(player.rect):
                player.take_damage()
                proj.alive = False
                self.projectiles.remove(proj)

    def try_special_attack(self, player):
        if not self.alive or not self.active:
            return False
        now = pygame.time.get_ticks()
        if now - self.special_cooldown < self.special_rate:
            return False

        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = math.sqrt(dx * dx + dy * dy)

        if distance <= BOSS_SPECIAL_RANGE * 2:
            self.special_cooldown = now
            for i in range(3):
                angle = (i * 120 + random.randint(-15, 15)) * math.pi / 180
                proj_x = self.rect.centerx + math.cos(angle) * 30
                proj_y = self.rect.centery + math.sin(angle) * 30
                target_x = proj_x + math.cos(angle) * 100
                target_y = proj_y + math.sin(angle) * 100
                self.projectiles.append(
                    BossProjectile(proj_x, proj_y, target_x, target_y, BOSS_SPECIAL_DAMAGE)
                )
            return True
        return False

    def take_damage(self, damage):
        if not self.alive or not self.active:
            return False
        self.health -= damage
        self.knockback_timer = pygame.time.get_ticks()
        if self.health <= 0:
            self.alive = False
            return True
        return False

    def can_attack(self, player):
        if not self.alive or not self.active:
            return False
        now = pygame.time.get_ticks()
        if now - self.attack_cooldown < self.attack_rate:
            return False
        return self.rect.colliderect(player.rect)

    def do_attack(self):
        self.attack_cooldown = pygame.time.get_ticks()
        return self.damage

    def draw(self, surface, camera_x=0, camera_y=0):
        if not self.alive or not self.active:
            return
        draw_x = self.rect.x - camera_x
        draw_y = self.rect.y - camera_y

        now = pygame.time.get_ticks()
        if self.knockback_timer > 0 and now - self.knockback_timer < 200:
            if (now // 50) % 2 == 0:
                return

        surface.blit(self.sprite, (draw_x, draw_y))

        for proj in self.projectiles:
            proj.draw(surface, camera_x, camera_y)

        bar_width = self.rect.width
        bar_height = 6
        bar_x = draw_x
        bar_y = draw_y - 10
        pygame.draw.rect(surface, COLOR_RED, (bar_x, bar_y, bar_width, bar_height))
        health_ratio = self.health / self.max_health
        pygame.draw.rect(
            surface, COLOR_GREEN,
            (bar_x, bar_y, int(bar_width * health_ratio), bar_height)
        )
        pygame.draw.rect(surface, COLOR_BLACK, (bar_x, bar_y, bar_width, bar_height), 1)

        hp_text = f"{self.health}/{self.max_health}"
        hp_surf = pygame.font.Font(None, 18).render(hp_text, True, COLOR_WHITE)
        hp_rect = hp_surf.get_rect(centerx=bar_x + bar_width // 2, bottom=bar_y - 2)
        surface.blit(hp_surf, hp_rect)
