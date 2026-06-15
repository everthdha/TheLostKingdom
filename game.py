import pygame
import sys
import os
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, CAMERA_ZOOM,
    COLOR_WHITE, COLOR_BLACK, COLOR_RED, COLOR_YELLOW, COLOR_GREEN,
    FONT_SIZE_LARGE, FONT_SIZE_MEDIUM, FONT_SIZE_SMALL,
    PLAYER_ATTACK_DAMAGE, BACKGROUNDS_DIR
)
from map_loader import GameMap
from player import Player
from enemy import HordeManager
from boss import Boss
from items import Key
from audio import AudioManager


class GameState:
    MENU = "menu"
    PLAYING = "playing"
    GAME_OVER = "game_over"
    VICTORY = "victory"
    PAUSED = "paused"


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("The Lost Kingdom")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MENU

        self.font_large = pygame.font.Font(None, FONT_SIZE_LARGE)
        self.font_medium = pygame.font.Font(None, FONT_SIZE_MEDIUM)
        self.font_small = pygame.font.Font(None, FONT_SIZE_SMALL)

        self.viewport_w = int(SCREEN_WIDTH * CAMERA_ZOOM)
        self.viewport_h = int(SCREEN_HEIGHT * CAMERA_ZOOM)
        self.viewport = pygame.Surface((self.viewport_w, self.viewport_h))
        self.hud_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        self.game_map = None
        self.player = None
        self.horde_manager = None
        self.boss = None
        self.key_item = None
        self.has_key = False
        self.camera_x = 0
        self.camera_y = 0

        self.enemies_killed = 0
        self.hordes_completed = 0
        self._prev_horde_active = False

        self.bg_start = self._load_background("start_background.png")
        self.bg_gameover = self._load_background("gameover_background.jpg")
        self.bg_victory = self._load_background("victory_background.png")

        self.audio = AudioManager()
        self.audio.play_music("menu")

    def new_game(self):
        self.game_map = GameMap("sin nombre.tmx")
        spawn = self.game_map.get_player_spawn()
        if spawn[0] is not None:
            sx, sy = spawn
        else:
            sx, sy = 200, 200

        self.player = Player(sx, sy, self.audio)
        self.horde_manager = HordeManager()

        bounds = self.game_map.get_map_bounds()
        boss_x = (bounds[0] + bounds[2]) // 2
        boss_y = (bounds[1] + bounds[3]) // 2
        self.boss = Boss(boss_x, boss_y)

        key_x = boss_x - 100
        key_y = boss_y - 100
        self.key_item = Key(key_x, key_y)
        self.has_key = False
        self.enemies_killed = 0
        self.hordes_completed = 0
        self._prev_horde_active = False
        self.state = GameState.PLAYING
        self.audio.play_music("game")

        self.horde_manager.start_next_horde(
            self.game_map, player_pos=(self.player.rect.centerx, self.player.rect.centery)
        )

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU:
                    if event.key == pygame.K_RETURN:
                        self.audio.play_music("game")
                        self.new_game()

                elif self.state == GameState.PLAYING:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PAUSED
                    elif event.key == pygame.K_SPACE:
                        attack_rect = self.player.attack()
                        if attack_rect:
                            self._process_attack(attack_rect)

                elif self.state == GameState.PAUSED:
                    if event.key == pygame.K_ESCAPE:
                        self.state = GameState.PLAYING

                elif self.state == GameState.GAME_OVER:
                    if event.key == pygame.K_r:
                        self.new_game()
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False

                elif self.state == GameState.VICTORY:
                    if event.key == pygame.K_RETURN:
                        self.state = GameState.MENU
                        self.audio.play_music("menu")
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False

    def _process_attack(self, attack_rect):
        for enemy in self.horde_manager.enemies[:]:
            if attack_rect.colliderect(enemy.rect):
                killed = enemy.take_damage(PLAYER_ATTACK_DAMAGE)
                if killed:
                    self.enemies_killed += 1

        if self.boss.active and self.boss.alive:
            if attack_rect.colliderect(self.boss.rect):
                killed = self.boss.take_damage(PLAYER_ATTACK_DAMAGE)
                if killed:
                    self.audio.play_sfx("boss_death")

    def update(self):
        if self.state != GameState.PLAYING:
            return

        dt = self.clock.get_time()

        keys = pygame.key.get_pressed()
        self.player.handle_input(keys, self.game_map)
        self.player.update(dt)

        self.horde_manager.update(self.player, self.game_map, dt)

        if self._prev_horde_active and not self.horde_manager.horde_active:
            self.hordes_completed += 1
        self._prev_horde_active = self.horde_manager.horde_active

        if self.horde_manager.all_hordes_complete and not self.key_item.collected:
            self.key_item.show()

        self.key_item.update(dt)
        if self.key_item.check_collect(self.player):
            self.has_key = True
            self.audio.play_sfx("key")
            self.boss.unlock()

        if self.boss.active:
            self.boss.update(self.player, self.game_map, dt)
            self.boss.try_special_attack(self.player)
            if self.boss.can_attack(self.player):
                self.player.take_damage()
                self.boss.do_attack()

        self._update_camera()

        if not self.player.alive:
            self.state = GameState.GAME_OVER

        if self.boss.active and not self.boss.alive:
            self.state = GameState.VICTORY

    def _update_camera(self):
        self.camera_x = self.player.rect.centerx - self.viewport_w // 2
        self.camera_y = self.player.rect.centery - self.viewport_h // 2

        bounds = self.game_map.get_map_bounds()
        map_min_x, map_min_y, map_max_x, map_max_y = bounds

        self.camera_x = max(map_min_x, min(self.camera_x, map_max_x - self.viewport_w))
        self.camera_y = max(map_min_y, min(self.camera_y, map_max_y - self.viewport_h))

        if map_max_x - map_min_x <= self.viewport_w:
            self.camera_x = map_min_x
        if map_max_y - map_min_y <= self.viewport_h:
            self.camera_y = map_min_y

    def _load_background(self, filename):
        path = os.path.join(BACKGROUNDS_DIR, filename)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert()
                return pygame.transform.smoothscale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            except Exception:
                pass
        return None

    def draw(self):
        self.screen.fill(COLOR_BLACK)

        if self.state == GameState.MENU:
            self._draw_menu()
        elif self.state == GameState.PLAYING:
            self._draw_game()
        elif self.state == GameState.PAUSED:
            self._draw_game()
            self._draw_pause()
        elif self.state == GameState.GAME_OVER:
            self._draw_game()
            self._draw_game_over()
        elif self.state == GameState.VICTORY:
            self._draw_game()
            self._draw_victory()

        pygame.display.flip()

    def _draw_menu(self):
        if self.bg_start:
            self.screen.blit(self.bg_start, (0, 0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("THE LOST KINGDOM", True, COLOR_YELLOW)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.screen.blit(title, title_rect)

        start = self.font_medium.render("Presiona ENTER para comenzar", True, COLOR_WHITE)
        start_rect = start.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        self.screen.blit(start, start_rect)

        controls = [
            "WASD - Mover",
            "ESPACIO - Atacar",
            "ESC - Pausar"
        ]
        for i, text in enumerate(controls):
            ctrl = self.font_small.render(text, True, COLOR_WHITE)
            ctrl_rect = ctrl.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80 + i * 30))
            self.screen.blit(ctrl, ctrl_rect)

    def _draw_game(self):
        self.viewport.fill(COLOR_BLACK)
        self.game_map.render(self.viewport, self.camera_x, self.camera_y)

        self.key_item.draw(self.viewport, self.camera_x, self.camera_y)

        self.player.draw(self.viewport, self.camera_x, self.camera_y)
        self.horde_manager.draw(self.viewport, self.camera_x, self.camera_y)

        if self.boss.active:
            self.boss.draw(self.viewport, self.camera_x, self.camera_y)

        scaled = pygame.transform.scale(self.viewport, (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.screen.blit(scaled, (0, 0))

        self.player.draw_hearts(self.screen)
        self.horde_manager.draw_horde_info(self.screen, self.font_medium)

        if self.has_key:
            key_text = self.font_small.render("Llave obtenida! Busca al boss", True, COLOR_YELLOW)
            self.screen.blit(key_text, (20, 60))

    def _draw_pause(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        pause_text = self.font_large.render("PAUSA", True, COLOR_WHITE)
        pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
        self.screen.blit(pause_text, pause_rect)

        resume_text = self.font_small.render("Presiona ESC para continuar", True, COLOR_WHITE)
        resume_rect = resume_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
        self.screen.blit(resume_text, resume_rect)

    def _draw_game_over(self):
        if self.bg_gameover:
            self.screen.blit(self.bg_gameover, (0, 0))
        else:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (0, 0))

        go_text = self.font_large.render("GAME OVER", True, COLOR_RED)
        go_rect = go_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        self.screen.blit(go_text, go_rect)

        stats_y = SCREEN_HEIGHT // 2 - 30
        hordes_text = self.font_medium.render(
            f"Hordas completadas: {self.hordes_completed}", True, COLOR_WHITE
        )
        hordes_rect = hordes_text.get_rect(center=(SCREEN_WIDTH // 2, stats_y))
        self.screen.blit(hordes_text, hordes_rect)

        kills_text = self.font_medium.render(
            f"Enemigos eliminados: {self.enemies_killed}", True, COLOR_WHITE
        )
        kills_rect = kills_text.get_rect(center=(SCREEN_WIDTH // 2, stats_y + 40))
        self.screen.blit(kills_text, kills_rect)

        restart = self.font_medium.render("R para reintentar", True, COLOR_YELLOW)
        restart_rect = restart.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
        self.screen.blit(restart, restart_rect)

        quit_text = self.font_small.render("ESC para salir", True, COLOR_WHITE)
        quit_rect = quit_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
        self.screen.blit(quit_text, quit_rect)

    def _draw_victory(self):
        if self.bg_victory:
            self.screen.blit(self.bg_victory, (0, 0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
        else:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

        win_text = self.font_large.render("VICTORIA!", True, COLOR_YELLOW)
        win_rect = win_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4))
        self.screen.blit(win_text, win_rect)

        msg = self.font_medium.render("Has derrotado al boss!", True, COLOR_WHITE)
        msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 + 20))
        self.screen.blit(msg, msg_rect)

        stats_y = SCREEN_HEIGHT // 2
        hordes_text = self.font_medium.render(
            f"Hordas completadas: {self.hordes_completed}", True, COLOR_WHITE
        )
        hordes_rect = hordes_text.get_rect(center=(SCREEN_WIDTH // 2, stats_y))
        self.screen.blit(hordes_text, hordes_rect)

        kills_text = self.font_medium.render(
            f"Enemigos eliminados: {self.enemies_killed}", True, COLOR_WHITE
        )
        kills_rect = kills_text.get_rect(center=(SCREEN_WIDTH // 2, stats_y + 40))
        self.screen.blit(kills_text, kills_rect)

        restart = self.font_small.render(
            "ENTER para menu principal | ESC para salir", True, COLOR_YELLOW
        )
        restart_rect = restart.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
        self.screen.blit(restart, restart_rect)

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()
