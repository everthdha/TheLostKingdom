import pygame
import os
from settings import MUSIC_DIR, SOUNDS_DIR, MUSIC_VOLUME, SFX_VOLUME


class AudioManager:
    def __init__(self):
        self.music_volume = MUSIC_VOLUME
        self.sfx_volume = SFX_VOLUME
        self.sounds = {}
        self.current_music = None
        self._initialized = False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._initialized = True
            self._load_all()
        except Exception:
            self._initialized = False

    def _load_all(self):
        self._music_paths = {}
        music_files = {"menu": "menu.mp3", "game": "game.mp3"}
        for key, filename in music_files.items():
            path = os.path.join(MUSIC_DIR, filename)
            if os.path.exists(path):
                self._music_paths[key] = path

        sfx_files = {
            "footsteps": "footsteps.wav.mp3",
            "sword": "sword.wav.mp3",
            "hit": "hit.wav.mp3",
            "death": "death.wav.mp3",
            "boss_death": "boss_death.wav.mp3",
            "key": "key.wav.mp3",
        }
        for key, filename in sfx_files.items():
            path = os.path.join(SOUNDS_DIR, filename)
            if os.path.exists(path):
                try:
                    sound = pygame.mixer.Sound(path)
                    sound.set_volume(self.sfx_volume)
                    self.sounds[key] = sound
                except Exception:
                    pass

    def play_music(self, name):
        if not self._initialized:
            return
        path = self._music_paths.get(name)
        if path:
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1)
                self.current_music = name
            except Exception:
                pass

    def stop_music(self):
        if self._initialized:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def play_sfx(self, name, loops=0):
        if not self._initialized:
            return
        sound = self.sounds.get(name)
        if sound:
            try:
                sound.play(loops)
            except Exception:
                pass

    def stop_sfx(self, name):
        if not self._initialized:
            return
        sound = self.sounds.get(name)
        if sound:
            try:
                sound.stop()
            except Exception:
                pass

    def set_music_volume(self, volume):
        self.music_volume = max(0.0, min(1.0, volume))
        if self._initialized:
            pygame.mixer.music.set_volume(self.music_volume)

    def set_sfx_volume(self, volume):
        self.sfx_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.sfx_volume)
