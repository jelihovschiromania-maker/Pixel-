"""
Pixel Survival - joc 2D de supravietuire pentru Android
Scris cu Kivy (fara HTML). Se compileaza in APK cu Buildozer + GitHub Actions.
"""

import math
import random

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.clock import Clock
from kivy.metrics import dp

Window.clearcolor = (0.05, 0.05, 0.09, 1)

# ---------------------------------------------------------------------------
# Constante
# ---------------------------------------------------------------------------
TILE = 48
WORLD_SIZE = 60
DAY_LENGTH = 240.0          # secunde pentru un ciclu zi/noapte complet
MAX_ENEMIES = 14
INTERACT_RANGE = 1.5
BUILD_RANGE = 3.5

TERRAIN_COLORS = {
    'grass': (0.29, 0.55, 0.24, 1),
    'forest': (0.16, 0.38, 0.16, 1),
    'sand': (0.76, 0.69, 0.45, 1),
    'stone': (0.5, 0.5, 0.52, 1),
    'water': (0.16, 0.35, 0.62, 1),
}

RESOURCE_COLORS = {
    'tree': (0.36, 0.22, 0.09, 1),
    'rock': (0.62, 0.62, 0.64, 1),
    'bush': (0.66, 0.13, 0.2, 1),
    'iron': (0.75, 0.58, 0.42, 1),
}

BUILDING_COLORS = {
    'campfire': (0.95, 0.45, 0.1, 1),
    'wall': (0.4, 0.32, 0.24, 1),
}

ENEMY_COLORS = {
    'wolf': (0.75, 0.75, 0.8, 1),
    'zombie': (0.3, 0.55, 0.3, 1),
}

ENEMY_TYPES = {
    'wolf': {'hp': 30, 'speed': 2.6, 'damage': 8},
    'zombie': {'hp': 70, 'speed': 1.25, 'damage': 15},
}

FULL_AMOUNT = {'tree': 5, 'rock': 5, 'iron': 3, 'bush': 3}
RESPAWN_TIME = {'tree': 50, 'rock': 70, 'iron': 150, 'bush': 40}

COST_NAMES = {
    'wood': 'lemn', 'stone': 'piatra', 'fiber': 'fibra',
    'iron': 'fier', 'meat': 'carne', 'berries': 'fructe',
}

RECIPES = [
    {'id': 'axe', 'name': 'Topor', 'cost': {'wood': 4, 'stone': 2}, 'type': 'tool'},
    {'id': 'pickaxe', 'name': 'Tarnacop', 'cost': {'wood': 4, 'stone': 2}, 'type': 'tool'},
    {'id': 'spear', 'name': 'Sulita', 'cost': {'wood': 5, 'stone': 1}, 'type': 'weapon', 'damage': 18},
    {'id': 'sword', 'name': 'Sabie', 'cost': {'wood': 2, 'stone': 6}, 'type': 'weapon', 'damage': 28},
    {'id': 'iron_sword', 'name': 'Sabie de fier', 'cost': {'wood': 2, 'stone': 4, 'iron': 4}, 'type': 'weapon', 'damage': 45},
    {'id': 'campfire', 'name': 'Foc de tabara', 'cost': {'wood': 6, 'stone': 3}, 'type': 'building'},
    {'id': 'wall', 'name': 'Zid', 'cost': {'wood': 6}, 'type': 'building'},
    {'id': 'bandage', 'name': 'Bandaj', 'cost': {'fiber': 4}, 'type': 'consumable', 'heal': 25},
    {'id': 'cooked_meat', 'name': 'Carne fripta', 'cost': {'meat': 1}, 'type': 'consumable', 'food': 35, 'needs_fire': True},
]


def terrain_at(x, y):
    n = (math.sin(x * 0.21) + math.cos(y * 0.18) +
         math.sin((x + y) * 0.09) + math.cos((x - y) * 0.13))
    if n < -1.6:
        return 'water'
    elif n < -0.5:
        return 'sand'
    elif n < 0.9:
        return 'grass'
    elif n < 1.8:
        return 'forest'
    else:
        return 'stone'


def generate_world():
    resources = {}
    for x in range(WORLD_SIZE):
        for y in range(WORLD_SIZE):
            t = terrain_at(x, y)
            r = random.random()
            if t == 'forest' and r < 0.35:
                resources[(x, y)] = {'type': 'tree', 'amount': 5, 'respawn_at': None}
            elif t == 'stone' and r < 0.30:
                if random.random() < 0.15:
                    resources[(x, y)] = {'type': 'iron', 'amount': 3, 'respawn_at': None}
                else:
                    resources[(x, y)] = {'type': 'rock', 'amount': 5, 'respawn_at': None}
            elif t == 'grass' and r < 0.16:
                resources[(x, y)] = {'type': 'bush', 'amount': 3, 'respawn_at': None}
    return resources


def find_start_position():
    cx, cy = WORLD_SIZE // 2, WORLD_SIZE // 2
    for r in range(0, 20):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                x, y = cx + dx, cy + dy
                if 0 <= x < WORLD_SIZE and 0 <= y < WORLD_SIZE and terrain_at(x, y) != 'water':
                    return x + 0.5, y + 0.5
    return cx + 0.5, cy + 0.5


# ---------------------------------------------------------------------------
# Logica jocului (fara Kivy) - usor de testat separat
# ---------------------------------------------------------------------------
class GameState:
    def __init__(self):
        self.elapsed = 0.0
        sx, sy = find_start_position()
        self.player = {
            'x': sx, 'y': sy,
            'hp': 100, 'max_hp': 100,
            'hunger': 100, 'thirst': 100,
            'inventory': {'wood': 0, 'stone': 0, 'fiber': 0, 'berries': 0, 'meat': 0, 'iron': 0},
            'tools': set(),
            'weapon': None,
            'kills': 0,
            'facing': (0, -1),
        }
        self.resources = generate_world()
        self._clear_start_area()
        self.enemies = []
        self.buildings = {}
        self.spawn_timer = 5.0
        self.pending_build = None
        self.message = ''
        self.message_timer = 0.0
        self.game_over = False
        self.death_day = 1

    def _clear_start_area(self):
        cx, cy = int(self.player['x']), int(self.player['y'])
        for x in range(cx - 2, cx + 3):
            for y in range(cy - 2, cy + 3):
                self.resources.pop((x, y), None)

    def set_message(self, text):
        self.message = text
        self.message_timer = 2.2

    def darkness(self):
        phase = (self.elapsed % DAY_LENGTH) / DAY_LENGTH
        val = -math.cos(2 * math.pi * phase)
        return max(0.0, val)

    def day_count(self):
        return 1 + int(self.elapsed // DAY_LENGTH)

    def walkable(self, tx, ty):
        if not (0 <= tx < WORLD_SIZE and 0 <= ty < WORLD_SIZE):
            return False
        if terrain_at(tx, ty) == 'water':
            return False
        b = self.buildings.get((tx, ty))
        if b and b['type'] == 'wall':
            return False
        return True

    def move_player(self, dx, dy, dt):
        if self.game_over:
            return
        speed = 3.3
        p = self.player
        nx = p['x'] + dx * speed * dt
        ny = p['y'] + dy * speed * dt
        if self.walkable(int(round(nx)), int(round(p['y']))):
            p['x'] = max(0.5, min(WORLD_SIZE - 0.5, nx))
        if self.walkable(int(round(p['x'])), int(round(ny))):
            p['y'] = max(0.5, min(WORLD_SIZE - 0.5, ny))
        if dx or dy:
            p['facing'] = (dx, dy)

    def near_campfire(self):
        p = self.player
        for (bx, by), b in self.buildings.items():
            if b['type'] == 'campfire' and math.hypot(bx + 0.5 - p['x'], by + 0.5 - p['y']) < 2.5:
                return True
        return False

    def weapon_damage(self):
        w = self.player['weapon']
        if w is None:
            return 8
        for r in RECIPES:
            if r['id'] == w:
                return r['damage']
        return 8

    def can_afford(self, cost):
        inv = self.player['inventory']
        return all(inv.get(k, 0) >= v for k, v in cost.items())

    def spend(self, cost):
        inv = self.player['inventory']
        for k, v in cost.items():
            inv[k] -= v

    def craft(self, recipe):
        if recipe['type'] == 'building':
            if not self.can_afford(recipe['cost']):
                self.set_message('Resurse insuficiente')
                return False
            self.pending_build = recipe
            self.set_message('Atinge harta pentru a plasa')
            return True
        if not self.can_afford(recipe['cost']):
            self.set_message('Resurse insuficiente')
            return False
        if recipe.get('needs_fire') and not self.near_campfire():
            self.set_message('Trebuie sa fii langa un foc de tabara')
            return False
        self.spend(recipe['cost'])
        rtype = recipe['type']
        if rtype == 'tool':
            self.player['tools'].add(recipe['id'])
            self.set_message(recipe['name'] + ' creat!')
        elif rtype == 'weapon':
            self.player['weapon'] = recipe['id']
            self.set_message(recipe['name'] + ' echipat!')
        elif rtype == 'consumable':
            if recipe['id'] == 'bandage':
                self.player['hp'] = min(self.player['max_hp'], self.player['hp'] + recipe['heal'])
            elif recipe['id'] == 'cooked_meat':
                self.player['hunger'] = min(100, self.player['hunger'] + recipe['food'])
            self.set_message(recipe['name'] + ' folosit!')
        return True

    def place_building(self, tx, ty):
        recipe = self.pending_build
        if not recipe:
            return
        p = self.player
        if not self.can_afford(recipe['cost']):
            self.set_message('Resurse insuficiente')
            self.pending_build = None
            return
        if (tx, ty) in self.buildings or (tx, ty) in self.resources or terrain_at(tx, ty) == 'water':
            self.set_message('Nu poti construi aici')
            return
        if math.hypot(tx + 0.5 - p['x'], ty + 0.5 - p['y']) > BUILD_RANGE:
            self.set_message('Prea departe')
            return
        self.spend(recipe['cost'])
        self.buildings[(tx, ty)] = {'type': recipe['id'], 'hp': 100}
        self.set_message(recipe['name'] + ' construit!')
        self.pending_build = None

    def gather_node(self, pos, node):
        p = self.player
        t = node['type']
        if t == 'tree':
            amt = 2 if 'axe' in p['tools'] else 1
            p['inventory']['wood'] += amt
            node['amount'] -= 1
            self.set_message('+%d lemn' % amt)
        elif t == 'rock':
            amt = 2 if 'pickaxe' in p['tools'] else 1
            p['inventory']['stone'] += amt
            node['amount'] -= 1
            self.set_message('+%d piatra' % amt)
        elif t == 'iron':
            if 'pickaxe' not in p['tools']:
                self.set_message('Ai nevoie de un tarnacop!')
                return
            p['inventory']['iron'] += 1
            node['amount'] -= 1
            self.set_message('+1 minereu de fier')
        elif t == 'bush':
            got = random.randint(1, 2)
            p['inventory']['berries'] += got
            if random.random() < 0.3:
                p['inventory']['fiber'] += 1
            node['amount'] -= 1
            self.set_message('+%d fructe' % got)
        if node['amount'] <= 0:
            node['respawn_at'] = self.elapsed + RESPAWN_TIME.get(t, 60)

    def do_action(self):
        if self.game_over:
            return
        p = self.player
        target = None
        tdist = 999
        for e in self.enemies:
            d = math.hypot(e['x'] - p['x'], e['y'] - p['y'])
            if d < INTERACT_RANGE and d < tdist:
                target = e
                tdist = d
        if target:
            dmg = self.weapon_damage()
            target['hp'] -= dmg
            if target['hp'] <= 0:
                self.enemies.remove(target)
                got = random.randint(1, 2)
                p['inventory']['meat'] += got
                p['kills'] += 1
                self.set_message('Inamic invins! +%d carne' % got)
            else:
                self.set_message('Lovitura: -%d HP inamic' % dmg)
            return
        best = None
        bdist = 999
        for pos, node in self.resources.items():
            if node.get('respawn_at') is not None:
                continue
            d = math.hypot(pos[0] + 0.5 - p['x'], pos[1] + 0.5 - p['y'])
            if d < INTERACT_RANGE and d < bdist:
                best = pos
                bdist = d
        if best:
            self.gather_node(best, self.resources[best])
            return
        tx, ty = int(round(p['x'])), int(round(p['y']))
        for ax in range(tx - 1, tx + 2):
            for ay in range(ty - 1, ty + 2):
                if 0 <= ax < WORLD_SIZE and 0 <= ay < WORLD_SIZE and terrain_at(ax, ay) == 'water':
                    p['thirst'] = min(100, p['thirst'] + 35)
                    self.set_message('Ai baut apa')
                    return
        self.set_message('Nimic de facut aici')

    def maybe_spawn_enemy(self, dt):
        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return
        self.spawn_timer = 6.0
        max_enemies = min(MAX_ENEMIES, 6 + self.day_count())
        if len(self.enemies) >= max_enemies:
            return
        chance = 0.85 if self.darkness() > 0.5 else 0.22
        if random.random() < chance:
            self.spawn_one_enemy()

    def spawn_one_enemy(self):
        p = self.player
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(9, 13)
        ex = max(1.0, min(WORLD_SIZE - 1.0, p['x'] + math.cos(angle) * dist))
        ey = max(1.0, min(WORLD_SIZE - 1.0, p['y'] + math.sin(angle) * dist))
        if terrain_at(int(ex), int(ey)) == 'water':
            return
        etype = 'zombie' if (self.darkness() > 0.4 and random.random() < 0.6) else 'wolf'
        stats = ENEMY_TYPES[etype]
        self.enemies.append({
            'x': ex, 'y': ey, 'type': etype,
            'hp': stats['hp'], 'max_hp': stats['hp'],
            'speed': stats['speed'], 'damage': stats['damage'], 'atk_cd': 0.0,
        })

    def update_enemies(self, dt):
        p = self.player
        for e in self.enemies:
            dx = p['x'] - e['x']
            dy = p['y'] - e['y']
            dist = math.hypot(dx, dy)
            if dist > 0.75:
                e['x'] += dx / dist * e['speed'] * dt
                e['y'] += dy / dist * e['speed'] * dt
            e['atk_cd'] = max(0.0, e['atk_cd'] - dt)
            if dist <= 0.9 and e['atk_cd'] <= 0:
                p['hp'] -= e['damage']
                e['atk_cd'] = 1.1
                self.set_message('Ai fost atacat!')
        self.enemies = [e for e in self.enemies if e['hp'] > 0]

    def update_resources(self):
        for node in self.resources.values():
            ra = node.get('respawn_at')
            if ra is not None and self.elapsed >= ra:
                node['amount'] = FULL_AMOUNT.get(node['type'], 4)
                node['respawn_at'] = None

    def trigger_game_over(self):
        self.game_over = True
        self.death_day = self.day_count()

    def update(self, dt):
        if self.game_over:
            return
        self.elapsed += dt
        p = self.player
        p['hunger'] = max(0.0, p['hunger'] - dt * (100.0 / 300.0))
        p['thirst'] = max(0.0, p['thirst'] - dt * (100.0 / 220.0))
        if p['hunger'] <= 0 or p['thirst'] <= 0:
            p['hp'] -= dt * 6
        elif p['hunger'] > 45 and p['thirst'] > 45 and p['hp'] < p['max_hp']:
            regen = 6.0 if self.near_campfire() else 3.0
            p['hp'] = min(p['max_hp'], p['hp'] + dt * regen)
        self.update_enemies(dt)
        self.maybe_spawn_enemy(dt)
        self.update_resources()
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ''
        if p['hp'] <= 0:
            self.trigger_game_over()


# ---------------------------------------------------------------------------
# Widget-uri Kivy
# ---------------------------------------------------------------------------
class Joystick(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.radius = dp(58)
        self.knob_radius = dp(24)
        self.center_pos = (0, 0)
        self.touch_id = None
        self.vector = (0, 0)
        with self.canvas:
            Color(1, 1, 1, 0.22)
            self.bg_ellipse = Ellipse(size=(self.radius * 2, self.radius * 2))
            Color(1, 1, 1, 0.55)
            self.knob_ellipse = Ellipse(size=(self.knob_radius * 2, self.knob_radius * 2))
        self.bind(pos=self._update_center, size=self._update_center)
        self._update_center()

    def _update_center(self, *args):
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        self.center_pos = (cx, cy)
        self.bg_ellipse.pos = (cx - self.radius, cy - self.radius)
        self._set_knob(cx, cy)

    def _set_knob(self, x, y):
        self.knob_ellipse.pos = (x - self.knob_radius, y - self.knob_radius)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.touch_id is None:
            self.touch_id = touch.uid
            self._update_knob(touch)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.uid == self.touch_id:
            self._update_knob(touch)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.uid == self.touch_id:
            self.touch_id = None
            self.vector = (0, 0)
            self._set_knob(*self.center_pos)
            return True
        return super().on_touch_up(touch)

    def _update_knob(self, touch):
        cx, cy = self.center_pos
        dx = touch.x - cx
        dy = touch.y - cy
        dist = math.hypot(dx, dy)
        if dist > self.radius:
            dx = dx / dist * self.radius
            dy = dy / dist * self.radius
            dist = self.radius
        self._set_knob(cx + dx, cy + dy)
        if dist > 0:
            self.vector = (dx / self.radius, dy / self.radius)
        else:
            self.vector = (0, 0)


class GameWidget(Widget):
    def __init__(self, state, **kwargs):
        super().__init__(**kwargs)
        self.state = state

    def world_to_screen(self, tx, ty, cam_x, cam_y):
        sx = self.width / 2 + (tx - cam_x) * TILE
        sy = self.height / 2 + (ty - cam_y) * TILE
        return sx, sy

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            s = self.state
            if s.pending_build:
                cam_x, cam_y = s.player['x'], s.player['y']
                wx = (touch.x - self.width / 2) / TILE + cam_x
                wy = (touch.y - self.height / 2) / TILE + cam_y
                s.place_building(int(math.floor(wx)), int(math.floor(wy)))
            return True
        return super().on_touch_down(touch)

    def redraw(self):
        self.canvas.clear()
        s = self.state
        cam_x, cam_y = s.player['x'], s.player['y']
        w, h = self.width, self.height
        if w <= 0 or h <= 0:
            return
        tiles_w = int(w / TILE) + 3
        tiles_h = int(h / TILE) + 3
        x0 = int(cam_x - tiles_w / 2)
        y0 = int(cam_y - tiles_h / 2)
        with self.canvas:
            for tx in range(x0, x0 + tiles_w):
                for ty in range(y0, y0 + tiles_h):
                    if 0 <= tx < WORLD_SIZE and 0 <= ty < WORLD_SIZE:
                        Color(*TERRAIN_COLORS[terrain_at(tx, ty)])
                        sx, sy = self.world_to_screen(tx, ty, cam_x, cam_y)
                        Rectangle(pos=(sx, sy), size=(TILE, TILE))
            for (rx, ry), node in s.resources.items():
                if node.get('respawn_at') is not None:
                    continue
                if x0 <= rx <= x0 + tiles_w and y0 <= ry <= y0 + tiles_h:
                    Color(*RESOURCE_COLORS[node['type']])
                    sx, sy = self.world_to_screen(rx, ry, cam_x, cam_y)
                    Ellipse(pos=(sx + 8, sy + 8), size=(TILE - 16, TILE - 16))
            for (bx, by), b in s.buildings.items():
                Color(*BUILDING_COLORS[b['type']])
                sx, sy = self.world_to_screen(bx, by, cam_x, cam_y)
                Rectangle(pos=(sx + 4, sy + 4), size=(TILE - 8, TILE - 8))
            for e in s.enemies:
                Color(*ENEMY_COLORS[e['type']])
                sx, sy = self.world_to_screen(e['x'], e['y'], cam_x, cam_y)
                Ellipse(pos=(sx + 2, sy + 2), size=(TILE - 4, TILE - 4))
            Color(0.95, 0.85, 0.2, 1)
            psx, psy = self.world_to_screen(s.player['x'], s.player['y'], cam_x, cam_y)
            Ellipse(pos=(psx + 2, psy + 2), size=(TILE - 4, TILE - 4))
            darkness = s.darkness()
            if darkness > 0.01:
                Color(0, 0, 0, darkness * 0.65)
                Rectangle(pos=(0, 0), size=(w, h))


class StatBar(Widget):
    def __init__(self, color, **kwargs):
        super().__init__(**kwargs)
        self.value = 1.0
        with self.canvas:
            Color(0, 0, 0, 0.45)
            self.bg = Rectangle(pos=self.pos, size=self.size)
            Color(*color)
            self.fill = Rectangle(pos=self.pos, size=(self.width, self.height))
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.fill.pos = self.pos
        self.fill.size = (self.width * self.value, self.height)

    def set_value(self, v):
        self.value = max(0.0, min(1.0, v))
        self._redraw()


# ---------------------------------------------------------------------------
# Aplicatia principala
# ---------------------------------------------------------------------------
class SurvivalApp(App):
    def build(self):
        self.title = 'Pixel Survival'
        self.state = GameState()
        self.game_over_shown = False
        self._over_box = None

        root = FloatLayout()
        self.root_layout = root

        self.game_widget = GameWidget(self.state, size_hint=(1, 1))
        root.add_widget(self.game_widget)

        hud = BoxLayout(orientation='vertical', size_hint=(0.62, None), height=dp(112),
                         pos_hint={'x': 0.01, 'top': 0.99}, spacing=dp(2))
        self.day_label = Label(text='Ziua 1 - Zi', size_hint=(1, None), height=dp(22),
                                halign='left', valign='middle', font_size='15sp')
        self.day_label.bind(size=lambda w, *a: setattr(w, 'text_size', w.size))

        bars = BoxLayout(orientation='vertical', size_hint=(1, None), height=dp(42), spacing=dp(3))
        self.hp_bar = StatBar((0.8, 0.15, 0.15, 1), size_hint=(1, None), height=dp(12))
        self.hunger_bar = StatBar((0.8, 0.55, 0.1, 1), size_hint=(1, None), height=dp(12))
        self.thirst_bar = StatBar((0.15, 0.45, 0.85, 1), size_hint=(1, None), height=dp(12))
        bars.add_widget(self.hp_bar)
        bars.add_widget(self.hunger_bar)
        bars.add_widget(self.thirst_bar)

        self.inv_label = Label(text='', size_hint=(1, None), height=dp(20),
                                halign='left', valign='middle', font_size='13sp')
        self.inv_label.bind(size=lambda w, *a: setattr(w, 'text_size', w.size))

        self.equip_label = Label(text='', size_hint=(1, None), height=dp(18),
                                  halign='left', valign='middle', font_size='12sp')
        self.equip_label.bind(size=lambda w, *a: setattr(w, 'text_size', w.size))

        hud.add_widget(self.day_label)
        hud.add_widget(bars)
        hud.add_widget(self.inv_label)
        hud.add_widget(self.equip_label)
        root.add_widget(hud)

        self.message_label = Label(text='', size_hint=(1, None), height=dp(30),
                                    pos_hint={'x': 0, 'y': 0.14}, font_size='16sp',
                                    color=(1, 1, 0.6, 1))
        root.add_widget(self.message_label)

        self.joystick = Joystick(size_hint=(None, None), size=(dp(130), dp(130)),
                                  pos_hint={'x': 0.02, 'y': 0.04})
        root.add_widget(self.joystick)

        self.action_btn = Button(text='Actiune', size_hint=(None, None), size=(dp(110), dp(110)),
                                  pos_hint={'right': 0.98, 'y': 0.05})
        self.action_btn.bind(on_press=self.on_action)
        root.add_widget(self.action_btn)

        craft_btn = Button(text='Craft', size_hint=(None, None), size=(dp(90), dp(48)),
                            pos_hint={'right': 0.98, 'top': 0.98})
        craft_btn.bind(on_press=self.open_crafting)
        root.add_widget(craft_btn)

        Clock.schedule_interval(self.update, 1.0 / 30.0)
        return root

    def on_action(self, *args):
        self.state.do_action()

    def open_crafting(self, *args):
        s = self.state
        content = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(6))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter('height'))

        popup = Popup(title='Craftare', size_hint=(0.88, 0.85))

        for recipe in RECIPES:
            afford = s.can_afford(recipe['cost'])
            cost_str = ', '.join('%d %s' % (v, COST_NAMES.get(k, k)) for k, v in recipe['cost'].items())
            extra = ' [dmg %d]' % recipe['damage'] if recipe['type'] == 'weapon' else ''
            btn = Button(text='%s%s\n(%s)' % (recipe['name'], extra, cost_str),
                         size_hint_y=None, height=dp(58), disabled=not afford,
                         halign='center')
            btn.bind(size=lambda w, *a: setattr(w, 'text_size', (w.width * 0.9, None)))

            def make_handler(r=recipe, p=popup):
                def handler(_inst):
                    self.state.craft(r)
                    p.dismiss()
                return handler

            btn.bind(on_press=make_handler())
            grid.add_widget(btn)

        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(grid)
        content.add_widget(sv)

        close_btn = Button(text='Inchide', size_hint_y=None, height=dp(44))
        close_btn.bind(on_press=popup.dismiss)
        content.add_widget(close_btn)

        popup.content = content
        popup.open()

    def refresh_hud(self):
        s = self.state
        p = s.player
        phase_name = 'Noapte' if s.darkness() > 0.5 else 'Zi'
        self.day_label.text = 'Ziua %d - %s' % (s.day_count(), phase_name)
        self.hp_bar.set_value(p['hp'] / p['max_hp'])
        self.hunger_bar.set_value(p['hunger'] / 100.0)
        self.thirst_bar.set_value(p['thirst'] / 100.0)
        inv = p['inventory']
        self.inv_label.text = 'Lemn:%d Piatra:%d Fibra:%d Fructe:%d Carne:%d Fier:%d' % (
            inv['wood'], inv['stone'], inv['fiber'], inv['berries'], inv['meat'], inv['iron'])
        weapon_name = 'Pumni'
        if p['weapon']:
            for r in RECIPES:
                if r['id'] == p['weapon']:
                    weapon_name = r['name']
        tools = ', '.join(p['tools']) if p['tools'] else '-'
        self.equip_label.text = 'Arma: %s | Unelte: %s | Ucisi: %d' % (weapon_name, tools, p['kills'])
        self.message_label.text = s.message

    def update(self, dt):
        s = self.state
        if not s.game_over:
            dx, dy = self.joystick.vector
            if dx or dy:
                s.move_player(dx, dy, dt)
            s.update(dt)
        self.refresh_hud()
        self.game_widget.redraw()
        if s.game_over and not self.game_over_shown:
            self.show_game_over()

    def show_game_over(self):
        self.game_over_shown = True
        s = self.state
        box = FloatLayout()
        with box.canvas.before:
            Color(0, 0, 0, 0.75)
            self._over_bg = Rectangle(pos=box.pos, size=box.size)
        box.bind(pos=lambda w, *a: setattr(self._over_bg, 'pos', w.pos),
                 size=lambda w, *a: setattr(self._over_bg, 'size', w.size))

        lbl = Label(text='Ai murit!\nAi supravietuit %d zile\nInamici invinsi: %d' %
                          (s.death_day, s.player['kills']),
                    halign='center', pos_hint={'center_x': 0.5, 'center_y': 0.6},
                    font_size='22sp', size_hint=(0.9, None), height=dp(120))
        lbl.bind(size=lambda w, *a: setattr(w, 'text_size', w.size))

        restart = Button(text='Reincepe', size_hint=(None, None), size=(dp(170), dp(58)),
                          pos_hint={'center_x': 0.5, 'center_y': 0.32})
        restart.bind(on_press=self.restart_game)

        box.add_widget(lbl)
        box.add_widget(restart)
        self._over_box = box
        self.root_layout.add_widget(box)

    def restart_game(self, *args):
        if self._over_box is not None:
            self.root_layout.remove_widget(self._over_box)
            self._over_box = None
        self.game_over_shown = False
        self.state = GameState()
        self.game_widget.state = self.state


if __name__ == '__main__':
    SurvivalApp().run()
