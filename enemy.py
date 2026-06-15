import pygame
import math
import os
import random
from settings import (
    ENEMIES_DIR, ENEMY_SPEED, ENEMY_HEALTH, ENEMY_DAMAGE,
    ENEMY_CHASE_RANGE, ENEMY_ATTACK_RATE, ENEMY_AVOID_DIST,
    TILE_SIZE, COLOR_RED, COLOR_GREEN,
    HORDE_CONFIG, HORDE_DELAY, HORDE_MESSAGE_DURATION,
    DEBUG_SPAWNS
)


class Enemy:
    def __init__(self, x, y, speed_mult=1.0):
        self.x = float(x)
        self.y = float(y)
        self.speed = ENEMY_SPEED * speed_mult
        self.health = ENEMY_HEALTH
        self.max_health = ENEMY_HEALTH
        self.damage = ENEMY_DAMAGE
        self.alive = True
        self.chase_range = ENEMY_CHASE_RANGE
        self.attack_cooldown = 0
        self.attack_rate = ENEMY_ATTACK_RATE
        self.stuck_timer = 0
        self.stuck_directions = 0
        self.wander_angle = random.uniform(0, 6.2832)

        self.sprite = self._load_sprite()
        self.rect = self.sprite.get_rect()
        self.rect.center = (int(self.x), int(self.y))

    def _load_sprite(self):
        filepath = os.path.join(ENEMIES_DIR, "enemigo.png")
        sheet = pygame.image.load(filepath).convert_alpha()
        sheet_width = sheet.get_width()
        sheet_height = sheet.get_height()

        if sheet_width > TILE_SIZE * 2:
            frame_width = sheet_width // 3
            frame_height = sheet_height // 4
            sprite = sheet.subsurface((0, 0, frame_width, frame_height))
        else:
            sprite = sheet

        return pygame.transform.smoothscale(sprite, (TILE_SIZE, TILE_SIZE))

    def _try_move(self, game_map, dx, dy):
        new_rect = self.rect.copy()
        new_rect.x += int(dx)
        if not game_map.check_collision(new_rect):
            self.rect.x = new_rect.x
            return True
        return False

    def _try_move_y(self, game_map, dy):
        new_rect = self.rect.copy()
        new_rect.y += int(dy)
        if not game_map.check_collision(new_rect):
            self.rect.y = new_rect.y
            return True
        return False

    def _try_alternative_directions(self, game_map, primary_dx, primary_dy):
        if primary_dx == 0 and primary_dy == 0:
            return False

        base_angle = math.atan2(primary_dy, primary_dx)
        offsets = [0.5, -0.5, 1.0, -1.0, 1.5, -1.5, 2.0, -2.0]

        for offset in offsets:
            angle = base_angle + offset
            test_dx = math.cos(angle) * self.speed
            test_dy = math.sin(angle) * self.speed

            new_rect = self.rect.copy()
            new_rect.x += int(test_dx)
            new_rect.y += int(test_dy)
            if not game_map.check_collision(new_rect):
                self.rect.x = new_rect.x
                self.rect.y = new_rect.y
                return True

        return False

    def update(self, player, game_map, dt, other_enemies=None):
        if not self.alive:
            return

        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = math.sqrt(dx * dx + dy * dy)

        move_x = 0.0
        move_y = 0.0

        if distance < self.chase_range and distance > 0:
            nx = dx / distance
            ny = dy / distance
            move_x = nx * self.speed
            move_y = ny * self.speed

        if other_enemies:
            sep_x, sep_y = 0.0, 0.0
            count = 0
            for other in other_enemies:
                if other is self or not other.alive:
                    continue
                ox = self.rect.centerx - other.rect.centerx
                oy = self.rect.centery - other.rect.centery
                od = math.sqrt(ox * ox + oy * oy)
                if 0 < od < ENEMY_AVOID_DIST:
                    sep_x += ox / od
                    sep_y += oy / od
                    count += 1
            if count > 0:
                sep_x /= count
                sep_y /= count
                move_x += sep_x * self.speed * 1.2
                move_y += sep_y * self.speed * 1.2

        if move_x != 0 or move_y != 0:
            length = math.sqrt(move_x * move_x + move_y * move_y)
            if length > 0:
                move_x = (move_x / length) * self.speed
                move_y = (move_y / length) * self.speed

        moved_x = False
        moved_y = False

        if move_x != 0:
            moved_x = self._try_move(game_map, move_x, 0)

        if move_y != 0:
            moved_y = self._try_move_y(game_map, move_y)

        if not moved_x and not moved_y and (move_x != 0 or move_y != 0):
            self.stuck_timer += dt
            if self.stuck_timer > 200:
                self.stuck_directions += 1
                if self.stuck_directions > 4:
                    self.wander_angle = random.uniform(0, 6.2832)
                    self.stuck_directions = 0

                alt_moved = self._try_alternative_directions(
                    game_map, move_x, move_y
                )

                if not alt_moved:
                    self.wander_angle += random.uniform(0.5, 1.5)
                    wx = math.cos(self.wander_angle) * self.speed * 0.6
                    wy = math.sin(self.wander_angle) * self.speed * 0.6
                    self._try_move(game_map, wx, 0)
                    self._try_move_y(game_map, wy)

                self.stuck_timer = 0
        else:
            self.stuck_timer = 0
            if moved_x or moved_y:
                self.stuck_directions = 0

        self.x = float(self.rect.centerx)
        self.y = float(self.rect.centery)

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.alive = False
            return True
        return False

    def can_attack(self, player):
        if not self.alive:
            return False
        now = pygame.time.get_ticks()
        if now - self.attack_cooldown < self.attack_rate:
            return False
        return self.rect.colliderect(player.rect)

    def do_attack(self):
        self.attack_cooldown = pygame.time.get_ticks()
        return self.damage

    def draw(self, surface, camera_x=0, camera_y=0):
        if not self.alive:
            return
        draw_x = self.rect.x - camera_x
        draw_y = self.rect.y - camera_y
        surface.blit(self.sprite, (draw_x, draw_y))


class HordeManager:
    def __init__(self):
        self.current_horde = 0
        self.enemies = []
        self.horde_active = False
        self.horde_delay = 0
        self.horde_message = ""
        self.horde_message_timer = 0
        self.all_hordes_complete = False
        self.horde_start_timer = 0
        self.show_start_message = False
        self.target_count = 0
        self.respawn_timer = 0
        self.respawn_delay = 800

    def start_next_horde(self, game_map, player_pos=None):
        self.current_horde += 1
        if self.current_horde > len(HORDE_CONFIG):
            self.all_hordes_complete = True
            return

        self.target_count = HORDE_CONFIG[self.current_horde]
        speed_mult = 1.0 + (self.current_horde - 1) * 0.05

        self.enemies = []
        spawn_points = game_map.get_enemy_spawn_points(
            self.target_count, player_pos=player_pos
        )
        for sx, sy in spawn_points:
            self.enemies.append(Enemy(sx, sy, speed_mult))

        self.horde_active = True
        self.horde_message = f"Horda {self.current_horde} - {self.target_count} enemigos"
        self.horde_message_timer = pygame.time.get_ticks()
        self.show_start_message = True
        self.horde_start_timer = pygame.time.get_ticks()
        self.respawn_timer = 0

        if DEBUG_SPAWNS:
            print(f"[HORDA] {self.current_horde} iniciada con {self.target_count} enemigos")

    def _respawn_enemy(self, game_map, player_pos, speed_mult):
        spawn_points = game_map.get_enemy_spawn_points(
            1, player_pos=player_pos,
            existing_enemies=[e for e in self.enemies if e.alive]
        )
        if spawn_points:
            sx, sy = spawn_points[0]
            if DEBUG_SPAWNS:
                print(f"[RESPAWN] Nuevo enemigo en ({sx},{sy})")
            return Enemy(sx, sy, speed_mult)
        return None

    def update(self, player, game_map, dt):
        now = pygame.time.get_ticks()

        if self.show_start_message and now - self.horde_start_timer >= HORDE_MESSAGE_DURATION:
            self.show_start_message = False

        if not self.horde_active:
            if self.horde_delay > 0 and now - self.horde_delay >= HORDE_DELAY:
                self.horde_delay = 0
                self.start_next_horde(
                    game_map,
                    player_pos=(player.rect.centerx, player.rect.centery)
                )
            return

        alive_enemies = [e for e in self.enemies if e.alive]

        for enemy in alive_enemies:
            enemy.update(player, game_map, dt, other_enemies=alive_enemies)

            if enemy.can_attack(player):
                player.take_damage()
                enemy.do_attack()

        self.enemies = [e for e in self.enemies if e.alive]

        alive_count = len(self.enemies)
        if alive_count < self.target_count:
            self.respawn_timer += dt
            if self.respawn_timer >= self.respawn_delay:
                self.respawn_timer = 0
                speed_mult = 1.0 + (self.current_horde - 1) * 0.05
                player_pos = (player.rect.centerx, player.rect.centery)
                new_enemy = self._respawn_enemy(game_map, player_pos, speed_mult)
                if new_enemy:
                    self.enemies.append(new_enemy)

        if len(self.enemies) <= 0 and self.horde_active:
            self.horde_active = False
            self.horde_delay = now
            self.horde_message = f"Horda {self.current_horde} completada!"
            self.horde_message_timer = now
            self.show_start_message = True
            self.horde_start_timer = now

    def draw(self, surface, camera_x=0, camera_y=0):
        for enemy in self.enemies:
            enemy.draw(surface, camera_x, camera_y)

    def draw_horde_info(self, surface, font):
        now = pygame.time.get_ticks()

        if self.show_start_message and now - self.horde_start_timer < HORDE_MESSAGE_DURATION:
            text = font.render(self.horde_message, True, COLOR_RED)
            text_rect = text.get_rect(center=(surface.get_width() // 2, 80))
            surface.blit(text, text_rect)
        elif not self.show_start_message and self.horde_message and now - self.horde_message_timer < HORDE_MESSAGE_DURATION:
            text = font.render(self.horde_message, True, COLOR_GREEN)
            text_rect = text.get_rect(center=(surface.get_width() // 2, 80))
            surface.blit(text, text_rect)

        if self.horde_active:
            info = f"Horda {self.current_horde}/10 | Enemigos: {len(self.enemies)}"
            text = font.render(info, True, COLOR_RED)
            text_rect = text.get_rect(center=(surface.get_width() // 2, 50))
            surface.blit(text, text_rect)
