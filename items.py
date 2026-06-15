import pygame
import os
from settings import ITEMS_DIR, TILE_SIZE, COLOR_YELLOW


class Key:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.collected = False
        self.visible = False

        self.sprite = self._load_sprite()
        self.rect = self.sprite.get_rect()
        self.rect.center = (x, y)

        self.bob_timer = 0
        self.bob_offset = 0

    def _load_sprite(self):
        key_files = [f for f in os.listdir(ITEMS_DIR) if f.endswith('.png')]
        if key_files:
            filepath = os.path.join(ITEMS_DIR, key_files[0])
        else:
            surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(surf, COLOR_YELLOW, (4, 2, 8, 12))
            pygame.draw.rect(surf, COLOR_YELLOW, (6, 0, 4, 4))
            return surf

        sheet = pygame.image.load(filepath).convert_alpha()
        sheet_width = sheet.get_width()
        sheet_height = sheet.get_height()

        if sheet_width > TILE_SIZE * 2:
            frame_width = sheet_width // 4
            frame_height = sheet_height // 1
            sprite = sheet.subsurface((0, 0, frame_width, frame_height))
        else:
            sprite = sheet

        return pygame.transform.scale(sprite, (TILE_SIZE, TILE_SIZE))

    def show(self):
        self.visible = True

    def update(self, dt):
        if not self.visible or self.collected:
            return

        self.bob_timer += dt
        self.bob_offset = int(3 * (self.bob_timer / 300) % 6 - 3)

    def check_collect(self, player):
        if not self.visible or self.collected:
            return False
        if self.rect.colliderect(player.rect):
            self.collected = True
            return True
        return False

    def draw(self, surface, camera_x=0, camera_y=0):
        if not self.visible or self.collected:
            return
        draw_x = self.rect.x - camera_x
        draw_y = self.rect.y - camera_y + self.bob_offset
        surface.blit(self.sprite, (draw_x, draw_y))
