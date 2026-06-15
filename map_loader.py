import os
import math
import xml.etree.ElementTree as ET
import pygame
from settings import (
    MAPS_DIR, TILE_SIZE, GRID_CELL_SIZE,
    ENEMY_SPAWN_MIN_DIST, ENEMY_SPAWN_MAX_DIST,
    ENEMY_SPAWN_CLEARANCE, ENEMY_MIN_SEPARATION, DEBUG_SPAWNS
)


class SpatialGrid:
    def __init__(self, cell_size):
        self.cell_size = cell_size
        self.cells = {}

    def clear(self):
        self.cells.clear()

    def _key(self, x, y):
        return (x // self.cell_size, y // self.cell_size)

    def insert(self, rect):
        min_k = self._key(rect.left, rect.top)
        max_k = self._key(rect.right, rect.bottom)
        for cx in range(min_k[0], max_k[0] + 1):
            for cy in range(min_k[1], max_k[1] + 1):
                key = (cx, cy)
                if key not in self.cells:
                    self.cells[key] = []
                self.cells[key].append(rect)

    def query(self, rect):
        min_k = self._key(rect.left, rect.top)
        max_k = self._key(rect.right, rect.bottom)
        seen = set()
        results = []
        for cx in range(min_k[0], max_k[0] + 1):
            for cy in range(min_k[1], max_k[1] + 1):
                key = (cx, cy)
                if key in self.cells:
                    for r in self.cells[key]:
                        rid = id(r)
                        if rid not in seen:
                            seen.add(rid)
                            results.append(r)
        return results


class GameMap:
    def __init__(self, filename):
        self.filename = os.path.join(MAPS_DIR, filename)
        self.tiles = {}
        self.collision_rects = []
        self.spatial_grid = SpatialGrid(GRID_CELL_SIZE)
        self.map_min_x = 0
        self.map_min_y = 0
        self.map_max_x = 0
        self.map_max_y = 0
        self.tile_image_cache = {}
        self.player_spawn = None
        self._parse_map()

    def _parse_map(self):
        tree = ET.parse(self.filename)
        root = tree.getroot()

        self.map_width = int(root.get('width', 0))
        self.map_height = int(root.get('height', 0))
        self.tile_width = int(root.get('tilewidth', TILE_SIZE))
        self.tile_height = int(root.get('tileheight', TILE_SIZE))

        tileset_sources = {}
        for tileset_elem in root.findall('tileset'):
            firstgid = int(tileset_elem.get('firstgid', 1))
            source = tileset_elem.get('source')
            if source:
                tileset_sources[firstgid] = source

        self.tile_images = {}
        for firstgid, source in tileset_sources.items():
            tsx_path = os.path.join(os.path.dirname(self.filename), source)
            if os.path.exists(tsx_path):
                self._load_tsx(tsx_path, firstgid)

        self._load_tileset_from_tmx(root)

        for layer_elem in root.findall('layer'):
            self._parse_tile_layer(layer_elem)

        for objgroup in root.findall('objectgroup'):
            name = objgroup.get('name', '')
            if name == 'Collisions':
                self._parse_collision_layer(objgroup)
            elif name == 'SpawnPoints':
                self._parse_spawn_points(objgroup)

        self._build_spatial_grid()

    def _load_tileset_from_tmx(self, root):
        for tileset_elem in root.findall('tileset'):
            firstgid = int(tileset_elem.get('firstgid', 1))
            tilecount = int(tileset_elem.get('tilecount', 0))
            columns = int(tileset_elem.get('columns', 0))

            image_elem = tileset_elem.find('image')
            if image_elem is not None:
                source = image_elem.get('source', '')
                img_path = os.path.join(os.path.dirname(self.filename), source)
                if os.path.exists(img_path):
                    image = pygame.image.load(img_path).convert_alpha()
                    tilewidth = int(tileset_elem.get('tilewidth', self.tile_width))
                    tileheight = int(tileset_elem.get('tileheight', self.tile_height))

                    if columns > 0 and tilecount > 0:
                        rows = (tilecount + columns - 1) // columns
                        for gid in range(tilecount):
                            actual_gid = firstgid + gid
                            col = gid % columns
                            row = gid // columns
                            frame = image.subsurface(
                                (col * tilewidth, row * tileheight, tilewidth, tileheight)
                            )
                            self.tile_images[actual_gid] = frame
                    else:
                        img_w = image.get_width()
                        img_h = image.get_height()
                        cols = img_w // tilewidth if tilewidth > 0 else 1
                        rows = img_h // tileheight if tileheight > 0 else 1
                        for gid in range(tilecount):
                            actual_gid = firstgid + gid
                            col = gid % cols
                            row = gid // cols
                            if row < rows:
                                frame = image.subsurface(
                                    (col * tilewidth, row * tileheight, tilewidth, tileheight)
                                )
                                self.tile_images[actual_gid] = frame

    def _load_tsx(self, tsx_path, firstgid):
        try:
            tree = ET.parse(tsx_path)
            root = tree.getroot()

            tilecount = int(root.get('tilecount', 0))
            columns = int(root.get('columns', 0))
            tilewidth = int(root.get('tilewidth', self.tile_width))
            tileheight = int(root.get('tileheight', self.tile_height))

            image_elem = root.find('image')
            if image_elem is None:
                return

            source = image_elem.get('source', '')
            if not source:
                return

            img_path = os.path.join(os.path.dirname(tsx_path), source)
            if not os.path.exists(img_path):
                return

            image = pygame.image.load(img_path).convert_alpha()

            if columns > 0 and tilecount > 0:
                for gid in range(tilecount):
                    actual_gid = firstgid + gid
                    col = gid % columns
                    row = gid // columns
                    frame = image.subsurface(
                        (col * tilewidth, row * tileheight, tilewidth, tileheight)
                    )
                    self.tile_images[actual_gid] = frame
            else:
                img_w = image.get_width()
                img_h = image.get_height()
                cols = img_w // tilewidth if tilewidth > 0 else 1
                rows = img_h // tileheight if tileheight > 0 else 1
                for gid in range(tilecount):
                    actual_gid = firstgid + gid
                    col = gid % cols
                    row = gid // cols
                    if row < rows:
                        frame = image.subsurface(
                            (col * tilewidth, row * tileheight, tilewidth, tileheight)
                        )
                        self.tile_images[actual_gid] = frame
        except Exception:
            pass

    def _parse_tile_layer(self, layer_elem):
        layer_name = layer_elem.get('name', '')
        data_elem = layer_elem.find('data')
        if data_elem is None:
            return

        encoding = data_elem.get('encoding', '')
        chunks = data_elem.findall('chunk')

        if chunks:
            for chunk in chunks:
                cx = int(chunk.get('x', 0))
                cy = int(chunk.get('y', 0))
                cw = int(chunk.get('width', 0))
                ch = int(chunk.get('height', 0))

                if encoding == 'csv':
                    text = chunk.text.strip()
                    values = [v.strip() for v in text.replace('\n', ',').split(',') if v.strip()]
                    idx = 0
                    for row_idx in range(ch):
                        for col_idx in range(cw):
                            if idx < len(values):
                                gid = int(values[idx]) if values[idx] else 0
                                idx += 1
                                if gid > 0:
                                    tile_x = cx + col_idx
                                    tile_y = cy + row_idx
                                    self.tiles[(tile_x, tile_y)] = gid
                                    world_x = tile_x * self.tile_width
                                    world_y = tile_y * self.tile_height
                                    if world_x < self.map_min_x:
                                        self.map_min_x = world_x
                                    if world_y < self.map_min_y:
                                        self.map_min_y = world_y
                                    if world_x + self.tile_width > self.map_max_x:
                                        self.map_max_x = world_x + self.tile_width
                                    if world_y + self.tile_height > self.map_max_y:
                                        self.map_max_y = world_y + self.tile_height
                else:
                    text = chunk.text.strip()
                    values = [v.strip() for v in text.replace('\n', ',').split(',') if v.strip()]
                    idx = 0
                    for row_idx in range(ch):
                        for col_idx in range(cw):
                            if idx < len(values):
                                gid = int(values[idx]) if values[idx] else 0
                                idx += 1
                                if gid > 0:
                                    tile_x = cx + col_idx
                                    tile_y = cy + row_idx
                                    self.tiles[(tile_x, tile_y)] = gid
                                    world_x = tile_x * self.tile_width
                                    world_y = tile_y * self.tile_height
                                    if world_x < self.map_min_x:
                                        self.map_min_x = world_x
                                    if world_y < self.map_min_y:
                                        self.map_min_y = world_y
                                    if world_x + self.tile_width > self.map_max_x:
                                        self.map_max_x = world_x + self.tile_width
                                    if world_y + self.tile_height > self.map_max_y:
                                        self.map_max_y = world_y + self.tile_height
        else:
            if encoding == 'csv':
                text = data_elem.text.strip()
                values = [v.strip() for v in text.replace('\n', ',').split(',') if v.strip()]
                idx = 0
                for row_idx in range(self.map_height):
                    for col_idx in range(self.map_width):
                        if idx < len(values):
                            gid = int(values[idx]) if values[idx] else 0
                            idx += 1
                            if gid > 0:
                                self.tiles[(col_idx, row_idx)] = gid
                                world_x = col_idx * self.tile_width
                                world_y = row_idx * self.tile_height
                                if world_x + self.tile_width > self.map_max_x:
                                    self.map_max_x = world_x + self.tile_width
                                if world_y + self.tile_height > self.map_max_y:
                                    self.map_max_y = world_y + self.tile_height

    def _parse_collision_layer(self, objgroup):
        self.collision_rects = []
        for obj in objgroup.findall('object'):
            x = float(obj.get('x', 0))
            y = float(obj.get('y', 0))

            rect_elem = obj.find('rect')
            poly_elem = obj.find('polygon')

            if rect_elem is not None:
                w = float(obj.get('width', 0))
                h = float(obj.get('height', 0))
                if w > 0 and h > 0:
                    self.collision_rects.append(pygame.Rect(x, y, w, h))

            elif poly_elem is not None:
                points_str = poly_elem.get('points', '')
                points = []
                for pt in points_str.split():
                    px, py = pt.split(',')
                    points.append((float(px), float(py)))

                if points:
                    min_px = min(p[0] for p in points)
                    min_py = min(p[1] for p in points)
                    max_px = max(p[0] for p in points)
                    max_py = max(p[1] for p in points)
                    w = max_px - min_px
                    h = max_py - min_py
                    if w > 0 and h > 0:
                        self.collision_rects.append(pygame.Rect(
                            x + min_px, y + min_py, w, h
                        ))

            else:
                w = float(obj.get('width', 0))
                h = float(obj.get('height', 0))
                if w > 0 and h > 0:
                    self.collision_rects.append(pygame.Rect(x, y, w, h))

    def _parse_spawn_points(self, objgroup):
        self.spawn_points = {}
        for obj in objgroup.findall('object'):
            name = obj.get('name', '')
            x = float(obj.get('x', 0))
            y = float(obj.get('y', 0))
            if name:
                self.spawn_points[name] = (x, y)

    def _build_spatial_grid(self):
        self.spatial_grid.clear()
        for rect in self.collision_rects:
            self.spatial_grid.insert(rect)

    def render(self, surface, camera_x=0, camera_y=0):
        start_col = int(camera_x // self.tile_width) - 1
        start_row = int(camera_y // self.tile_height) - 1
        end_col = int((camera_x + surface.get_width()) // self.tile_width) + 2
        end_row = int((camera_y + surface.get_height()) // self.tile_height) + 2

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                key = (col, row)
                if key in self.tiles:
                    gid = self.tiles[key]
                    if gid in self.tile_images:
                        img = self.tile_images[gid]
                        px = col * self.tile_width - camera_x
                        py = row * self.tile_height - camera_y
                        surface.blit(img, (px, py))

    def get_map_bounds(self):
        return (self.map_min_x, self.map_min_y, self.map_max_x, self.map_max_y)

    def check_collision(self, rect):
        nearby = self.spatial_grid.query(rect)
        for col_rect in nearby:
            if rect.colliderect(col_rect):
                return True
        return False

    def get_player_spawn(self):
        if not self.spawn_points:
            return None, None

        spawn_pos = self.spawn_points.get('PlayerSpawn')
        if spawn_pos is None:
            for name, pos in self.spawn_points.items():
                if 'player' in name.lower() or 'spawn' in name.lower():
                    spawn_pos = pos
                    break

        if spawn_pos is None:
            return None, None

        x, y = spawn_pos
        test_rect = pygame.Rect(x - 8, y - 8, 16, 16)
        if not self.check_collision(test_rect):
            return x, y

        free_pos = self.find_nearest_free_position(x, y)
        if free_pos:
            return free_pos

        return x, y

    def find_nearest_free_position(self, x, y, max_radius=100, step=8):
        import math
        for radius in range(step, max_radius + 1, step):
            for angle_deg in range(0, 360, 15):
                angle = math.radians(angle_deg)
                test_x = int(x + math.cos(angle) * radius)
                test_y = int(y + math.sin(angle) * radius)
                test_rect = pygame.Rect(test_x - 8, test_y - 8, 16, 16)
                if not self.check_collision(test_rect):
                    return (test_x, test_y)
        return None

    def get_spawn_points(self, count, margin=64, player_pos=None):
        bounds = self.get_map_bounds()
        min_x = bounds[0] + margin
        min_y = bounds[1] + margin
        max_x = bounds[2] - margin
        max_y = bounds[3] - margin

        if max_x <= min_x or max_y <= min_y:
            return [(400, 400)] * count

        import random
        points = []
        attempts = 0
        max_attempts = count * 20

        while len(points) < count and attempts < max_attempts:
            x = random.randint(int(min_x), int(max_x))
            y = random.randint(int(min_y), int(max_y))
            test_rect = pygame.Rect(x - 16, y - 16, 32, 32)
            if not self.check_collision(test_rect):
                if player_pos:
                    dx = x - player_pos[0]
                    dy = y - player_pos[1]
                    if (dx * dx + dy * dy) < 100 * 100:
                        attempts += 1
                        continue
                points.append((x, y))
            attempts += 1

        while len(points) < count:
            points.append((400, 400))

        return points

    def is_position_valid(self, x, y, clearance=None):
        if clearance is None:
            clearance = ENEMY_SPAWN_CLEARANCE

        half = clearance
        test_rect = pygame.Rect(x - half, y - half, clearance * 2, clearance * 2)
        if self.check_collision(test_rect):
            return False, "colision"

        center_rect = pygame.Rect(x - 6, y - 6, 12, 12)
        if self.check_collision(center_rect):
            return False, "centro bloqueado"

        bounds = self.get_map_bounds()
        margin = 16
        if (x < bounds[0] + margin or x > bounds[2] - margin or
                y < bounds[1] + margin or y > bounds[3] - margin):
            return False, "fuera de limites"

        return True, "ok"

    def get_enemy_spawn_points(self, count, player_pos=None, existing_enemies=None):
        import random

        if not player_pos:
            return self.get_spawn_points(count, margin=64)

        px, py = player_pos
        points = []
        attempts = 0
        max_attempts = count * 50

        if DEBUG_SPAWNS:
            print(f"[SPAWN] Buscando {count} posiciones para enemigos")

        while len(points) < count and attempts < max_attempts:
            angle = random.uniform(0, 6.2832)
            dist = random.uniform(ENEMY_SPAWN_MIN_DIST, ENEMY_SPAWN_MAX_DIST)
            x = int(px + math.cos(angle) * dist)
            y = int(py + math.sin(angle) * dist)

            dx = x - px
            dy = y - py
            dist_sq = dx * dx + dy * dy
            if dist_sq < ENEMY_SPAWN_MIN_DIST * ENEMY_SPAWN_MIN_DIST:
                attempts += 1
                if DEBUG_SPAWNS:
                    print(f"[SPAWN] Rechazado ({x},{y}) - muy cerca (dist={math.sqrt(dist_sq):.0f})")
                continue

            valid, reason = self.is_position_valid(x, y)
            if not valid:
                attempts += 1
                if DEBUG_SPAWNS:
                    print(f"[SPAWN] Rechazado ({x},{y}) - {reason}")
                continue

            too_close = False
            for sx, sy in points:
                ddx = x - sx
                ddy = y - sy
                if ddx * ddx + ddy * ddy < ENEMY_MIN_SEPARATION * ENEMY_MIN_SEPARATION:
                    too_close = True
                    break
            if too_close:
                attempts += 1
                if DEBUG_SPAWNS:
                    print(f"[SPAWN] Rechazado ({x},{y}) - muy cerca de otro spawn")
                continue

            if existing_enemies:
                for enemy in existing_enemies:
                    if not enemy.alive:
                        continue
                    edx = x - enemy.rect.centerx
                    edy = y - enemy.rect.centery
                    if edx * edx + edy * edy < ENEMY_MIN_SEPARATION * ENEMY_MIN_SEPARATION:
                        too_close = True
                        break
            if too_close:
                attempts += 1
                if DEBUG_SPAWNS:
                    print(f"[SPAWN] Rechazado ({x},{y}) - muy cerca de enemigo existente")
                continue

            points.append((x, y))
            if DEBUG_SPAWNS:
                print(f"[SPAWN] Aceptado ({x},{y}) - intento {attempts}")

            attempts += 1

        if DEBUG_SPAWNS:
            print(f"[SPAWN] Resultado: {len(points)}/{count} posiciones en {attempts} intentos")

        fallback_attempts = 0
        while len(points) < count and fallback_attempts < count * 20:
            angle = random.uniform(0, 6.2832)
            dist = random.uniform(ENEMY_SPAWN_MIN_DIST, ENEMY_SPAWN_MAX_DIST)
            x = int(px + math.cos(angle) * dist)
            y = int(py + math.sin(angle) * dist)
            valid, _ = self.is_position_valid(x, y)
            if valid:
                points.append((x, y))
                if DEBUG_SPAWNS:
                    print(f"[SPAWN] Fallback aceptado ({x},{y})")
            fallback_attempts += 1

        while len(points) < count:
            angle = random.uniform(0, 6.2832)
            dist = random.uniform(ENEMY_SPAWN_MIN_DIST, ENEMY_SPAWN_MAX_DIST)
            x = int(px + math.cos(angle) * dist)
            y = int(py + math.sin(angle) * dist)
            points.append((x, y))
            if DEBUG_SPAWNS:
                print(f"[SPAWN] Ultimo recurso ({x},{y}) - sin validacion")

        return points
