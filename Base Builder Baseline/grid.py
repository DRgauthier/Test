"""
MASTER DESIGN DOCUMENT

Role:
This module serves as the foundational spatial representation for the 2D base-building game. 
It provides an interactive, resizable grid world where terrain and structures are represented as tiles. 
It handles rendering with a dynamic zoom camera, spatial state, user input for editing, map navigation, 
building selection, and UI panels.

Modular Isolation Strategy:
This file encapsulates the grid and UI drawing. It allows external modules (like `entities.py`) 
to access the `grid` matrix, `health_map`, and `active_buildings` to read/modify states 
without tight coupling. It integrates `GameState` to handle economic transactions and capacities.

Core Data Structures/Specs:
- UIs: Left UI (Build Menu + Selection Stats), Right UI (Resources + Day Cycle).
- Active Buildings: Maps `(col, row)` to `{"type": str, "level": int, ...}`.
- Tile IDs: 
  - 4: Tower, 5: Barracks, 7: Command
  - 8: Farm Seed, 81: Grow, 82: Harvest
  - 9: Well Ready, 91: Well Dry
  - 20: Enemy Camp
"""

import pygame
import sys
import random
import math
from entities import EntityManager
from gamestate import GameState

class GridWorld:
    def __init__(self):
        pygame.init()
        self.screen_width = 900
        self.screen_height = 600
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), 
            pygame.RESIZABLE
        )
        pygame.display.set_caption("Grid World Foundation")
        
        self.ui_width = 200
        self.right_ui_width = 150
        self.world_cols = 100
        self.world_rows = 100
        
        # Base logical cell size is 40. Current visual size can change via zoom.
        self.logical_cell_size = 40 
        self.cell_size = 40
        
        self.grid = [[0 for _ in range(self.world_rows)] for _ in range(self.world_cols)]
        self.health_map = {}
        self.active_buildings = {}
        
        self.camera_x = 0
        self.camera_y = 0
        
        self.base_cmd_pos = None
        self.base_cmd_col = -1
        self.base_cmd_row = -1
        self.selected_tile = None
        
        self.colors = {
            0: (30, 30, 30),
            99: (50, 50, 60), 
            1: (200, 200, 200),
            11: (100, 150, 200),
            2: (139, 69, 19),
            12: (200, 150, 100),
            4: (150, 150, 150),
            14: (100, 100, 150),
            5: (100, 150, 100),
            15: (70, 100, 70),
            6: (150, 100, 100),
            16: (100, 70, 70),
            7: (200, 200, 255),
            17: (100, 100, 200),
            18: (100, 80, 50),  # Farm Blueprint
            8:  (139, 69, 19),  # Farm Seed
            81: (144, 238, 144),# Farm Grow
            82: (255, 215, 0),  # Farm Harvest
            19: (50, 100, 200), # Well Blueprint
            9:  (0, 191, 255),  # Well Ready
            91: (105, 105, 105),# Well Dry
            3: (34, 139, 34),   # Forest
            30: (120, 120, 130),# Ore
            33: (50, 200, 50),  # Marked Forest
            34: (180, 180, 190),# Marked Ore
            20: (139, 0, 0)
        }
        
        # UI brush definitions
        self.brushes = [
            {"id": 0, "name": "Eraser", "places": 0, "color": self.colors[0], "w": 1, "h": 1, "cost": {}},
            {"id": 7, "name": "Command", "places": 17, "color": self.colors[17], "w": 6, "h": 2, "cost": {}},
            {"id": 18, "name": "Farm", "places": 18, "color": self.colors[18], "w": 2, "h": 2, "cost": {"Wood": 20}},
            {"id": 19, "name": "Well", "places": 19, "color": self.colors[19], "w": 1, "h": 1, "cost": {"Wood": 50}},
            {"id": 1, "name": "Wall", "places": 11, "color": self.colors[11], "w": 1, "h": 1, "cost": {"Wood": 10}},
            {"id": 2, "name": "Door", "places": 12, "color": self.colors[12], "w": 1, "h": 1, "cost": {"Wood": 15}},
            {"id": 4, "name": "Tower", "places": 14, "color": self.colors[14], "w": 2, "h": 2, "cost": {"Wood": 100, "Ore": 50}},
            {"id": 5, "name": "Barracks", "places": 15, "color": self.colors[15], "w": 2, "h": 4, "cost": {"Wood": 150, "Food": 50}},
            {"id": 6, "name": "Range", "places": 16, "color": self.colors[16], "w": 2, "h": 6, "cost": {"Wood": 80}},
            {"id": 33, "name": "Harvest", "places": 33, "color": self.colors[33], "w": 1, "h": 1, "cost": {}}
        ]
        
        self.current_brush_idx = 1
        
        self.clock = pygame.time.Clock()
        self.is_running = True
        self.is_painting = False
        self.is_panning = False
        self.is_paused = False
        
        self.state = GameState()
        self.entity_manager = EntityManager()
        
        self.tower_aoe_surface = pygame.Surface((1200, 1200), pygame.SRCALPHA)
        pygame.draw.circle(self.tower_aoe_surface, (255, 50, 50, 30), (600, 600), 600)
        
        self._generate_world()

    def _generate_world(self):
        for _ in range(60):
            c = random.randint(0, self.world_cols - 1)
            r = random.randint(0, self.world_rows - 1)
            if self.grid[c][r] == 0:
                self.grid[c][r] = 3
                
        for _ in range(30):
            c = random.randint(0, self.world_cols - 1)
            r = random.randint(0, self.world_rows - 1)
            if self.grid[c][r] == 0:
                self.grid[c][r] = 30

        camps_spawned = 0
        while camps_spawned < 8:
            c = random.randint(0, self.world_cols - 1)
            r = random.randint(0, self.world_rows - 1)
            if c > 40 or r > 40:
                if self.grid[c][r] == 0:
                    self.grid[c][r] = 20
                    camps_spawned += 1

    @property
    def view_width(self):
        return max(1, self.screen_width - self.ui_width - self.right_ui_width)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            elif event.type == pygame.VIDEORESIZE:
                self.screen_width = event.w
                self.screen_height = event.h
                self.screen = pygame.display.set_mode(
                    (self.screen_width, self.screen_height), 
                    pygame.RESIZABLE
                )
                self.clamp_camera()
            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if self.ui_width < mx < self.screen_width - self.right_ui_width:
                    zoom_speed = 4
                    old_size = self.cell_size
                    self.cell_size += event.y * zoom_speed
                    self.cell_size = max(10, min(100, self.cell_size))
                    
                    if self.cell_size != old_size:
                        world_x = (mx - self.ui_width) + self.camera_x
                        world_y = my + self.camera_y
                        
                        col_f = world_x / old_size
                        row_f = world_y / old_size
                        
                        new_world_x = col_f * self.cell_size
                        new_world_y = row_f * self.cell_size
                        
                        self.camera_x = new_world_x - (mx - self.ui_width)
                        self.camera_y = new_world_y - my
                        
                        self.clamp_camera()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.is_paused = not self.is_paused
                elif event.key == pygame.K_0: self.current_brush_idx = 0
                elif event.key == pygame.K_1: self.current_brush_idx = 1
                elif event.key == pygame.K_2: self.current_brush_idx = 2
                elif event.key == pygame.K_3: self.current_brush_idx = 3
                elif event.key == pygame.K_e:
                    # Debug Emergency Toggle
                    self.entity_manager.debug_emergency = not getattr(self.entity_manager, 'debug_emergency', False)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if event.button == 1:
                    if mx <= self.ui_width:
                        self.handle_left_ui_click(my)
                    elif mx >= self.screen_width - self.right_ui_width:
                        pass # Right UI click
                    else:
                        # Clicked Map - Select Building or Pan
                        world_x = (mx - self.ui_width) + self.camera_x
                        world_y = my + self.camera_y
                        col = int(world_x // self.cell_size)
                        row = int(world_y // self.cell_size)
                        
                        found_bldg = None
                        for (bc, br), b_data in self.active_buildings.items():
                            w, h = 1, 1
                            if b_data["type"] == "COMMAND": w, h = 6, 2
                            elif b_data["type"] == "BARRACKS": w, h = 2, 4
                            elif b_data["type"] == "FARM": w, h = 2, 2
                            elif b_data["type"] == "WELL": w, h = 1, 1
                            if bc <= col < bc + w and br <= row < br + h:
                                found_bldg = (bc, br)
                                break
                                
                        if found_bldg:
                            self.selected_tile = found_bldg
                        else:
                            self.selected_tile = None
                            self.is_panning = True
                elif event.button == 3:
                    if self.ui_width < mx < self.screen_width - self.right_ui_width:
                        self.is_painting = True
                        self.paint_cell(mx, my)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.is_panning = False
                elif event.button == 3:
                    self.is_painting = False
            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                if self.is_panning and self.ui_width < mx < self.screen_width - self.right_ui_width:
                    self.camera_x -= event.rel[0]
                    self.camera_y -= event.rel[1]
                    self.clamp_camera()
                elif self.is_painting and self.ui_width < mx < self.screen_width - self.right_ui_width:
                    brush = self.brushes[self.current_brush_idx]
                    if brush["places"] in (0, 33):
                        self.paint_cell(mx, my)

    def handle_left_ui_click(self, y):
        if self.selected_tile and self.selected_tile in self.active_buildings:
            b_data = self.active_buildings[self.selected_tile]
            if b_data["type"] in ("COMMAND", "BARRACKS"):
                if 50 <= y <= 90:
                    lvl = b_data.get("level", 1)
                    cost = {"Wood": 100 * lvl}
                    if self.state.can_afford(cost):
                        self.state.deduct(cost)
                        b_data["level"] = lvl + 1
                        
        btn_height = 40
        start_y = 120
        idx = (y - start_y) // btn_height
        if 0 <= idx < len(self.brushes):
            self.current_brush_idx = idx
            self.selected_tile = None 

    def clamp_camera(self):
        max_x = max(0, self.world_cols * self.cell_size - self.view_width)
        max_y = max(0, self.world_rows * self.cell_size - self.screen_height)
        self.camera_x = max(0, min(self.camera_x, max_x))
        self.camera_y = max(0, min(self.camera_y, max_y))

    def paint_cell(self, screen_x, screen_y):
        world_x = (screen_x - self.ui_width) + self.camera_x
        world_y = screen_y + self.camera_y
        col = int(world_x // self.cell_size)
        row = int(world_y // self.cell_size)
        
        brush = self.brushes[self.current_brush_idx]
        w, h = brush["w"], brush["h"]
        places_id = brush["places"]
        
        if not (0 <= col and col + w <= self.world_cols and 0 <= row and row + h <= self.world_rows):
            return
            
        if places_id == 0:
            target_id = self.grid[col][row]
            if target_id in (1, 2, 4, 5, 6, 7, 8, 9, 81, 82, 91):
                key = (col, row)
                if key in self.health_map:
                    self.health_map[key][0] -= 2.0
                    if self.health_map[key][0] <= 0:
                        self.grid[col][row] = 0
                        del self.health_map[key]
                        if key in self.active_buildings:
                            del self.active_buildings[key]
                        if self.selected_tile == key:
                            self.selected_tile = None
            elif target_id != 0:
                self.grid[col][row] = 0
            return
            
        if places_id == 33:
            if self.grid[col][row] == 3:
                self.grid[col][row] = 33
            elif self.grid[col][row] == 30:
                self.grid[col][row] = 34
            return

        for c in range(col, col + w):
            for r in range(row, row + h):
                if self.grid[c][r] != 0:
                    return

        if not self.state.can_afford(brush["cost"]):
            return
            
        self.state.deduct(brush["cost"])
        
        if places_id == 17:
            self.grid[col][row] = 7 
            self.health_map[(col, row)] = [1000, 1000]
            self.active_buildings[(col, row)] = {"type": "COMMAND", "level": 1}
            self.base_cmd_col = col
            self.base_cmd_row = row
            cx = (col + 3) * self.logical_cell_size
            cy = (row + 1) * self.logical_cell_size
            self.base_cmd_pos = (cx, cy)
            self.entity_manager.spawn_initial(cx, cy + self.logical_cell_size)
        elif places_id == 15: # Barracks
            self.grid[col][row] = 15 # Blueprint
        else:
            self.grid[col][row] = places_id
        
        for c in range(col, col + w):
            for r in range(row, row + h):
                if c == col and r == row:
                    continue
                self.grid[c][r] = 99

    def draw_ui(self):
        font = pygame.font.SysFont(None, 24)
        small_font = pygame.font.SysFont(None, 16)

        # LEFT UI
        ui_rect = pygame.Rect(0, 0, self.ui_width, self.screen_height)
        pygame.draw.rect(self.screen, (40, 40, 45), ui_rect)
        pygame.draw.line(self.screen, (100, 100, 100), (self.ui_width, 0), (self.ui_width, self.screen_height), 2)
        
        start_y = 10
        # Selection Stats
        if self.selected_tile and self.selected_tile in self.active_buildings:
            b_data = self.active_buildings[self.selected_tile]
            t_type = b_data["type"]
            lvl = b_data.get("level", 1)
            
            title = font.render(f"SELECTED: {t_type}", True, (255, 255, 100))
            self.screen.blit(title, (10, start_y))
            start_y += 20
            lvl_text = small_font.render(f"Level: {lvl}", True, (200, 200, 200))
            self.screen.blit(lvl_text, (10, start_y))
            
            if t_type in ("COMMAND", "BARRACKS"):
                start_y += 20
                cost = {"Wood": 100 * lvl}
                pygame.draw.rect(self.screen, (60, 100, 60), (10, start_y, self.ui_width - 20, 40))
                upg_text = font.render(f"UPGRADE ({cost['Wood']} W)", True, (255, 255, 255))
                self.screen.blit(upg_text, (15, start_y + 10))
            
        else:
            title = font.render("BUILD MENU", True, (255, 255, 255))
            self.screen.blit(title, (20, start_y))

        # Brushes
        btn_height = 40
        start_y = 120
        for i, brush in enumerate(self.brushes):
            rect_y = start_y + (i * btn_height)
            
            if i == self.current_brush_idx and not self.selected_tile:
                pygame.draw.rect(self.screen, (80, 80, 90), (10, rect_y, self.ui_width - 20, 35))
                pygame.draw.rect(self.screen, (200, 200, 50), (10, rect_y, self.ui_width - 20, 35), 2)
            else:
                pygame.draw.rect(self.screen, (60, 60, 65), (10, rect_y, self.ui_width - 20, 35))
            
            pygame.draw.rect(self.screen, brush["color"], (15, rect_y + 5, 20, 20))
            pygame.draw.rect(self.screen, (255, 255, 255), (15, rect_y + 5, 20, 20), 1)
            
            name_text = font.render(brush['name'], True, (220, 220, 220))
            self.screen.blit(name_text, (45, rect_y + 5))
            dims_text = small_font.render(f"({brush['w']}x{brush['h']})", True, (150, 150, 150))
            self.screen.blit(dims_text, (45, rect_y + 20))
            
            cost_str = " ".join([f"{k}:{v}" for k,v in brush["cost"].items()]) if brush["cost"] else "Free"
            cost_text = small_font.render(cost_str, True, (200, 200, 100))
            self.screen.blit(cost_text, (90, rect_y + 20))

        # RIGHT UI
        rx = self.screen_width - self.right_ui_width
        right_rect = pygame.Rect(rx, 0, self.right_ui_width, self.screen_height)
        pygame.draw.rect(self.screen, (40, 40, 45), right_rect)
        pygame.draw.line(self.screen, (100, 100, 100), (rx, 0), (rx, self.screen_height), 2)
        
        ry = 10
        self.screen.blit(font.render("RESOURCES", True, (255, 255, 255)), (rx + 10, ry))
        ry += 25
        for res, amount in self.state.resources.items():
            text = font.render(f"{res}: {int(amount)}", True, (200, 200, 200))
            self.screen.blit(text, (rx + 10, ry))
            ry += 20
            
        pygame.draw.line(self.screen, (80, 80, 80), (rx + 10, ry + 5), (rx + self.right_ui_width - 10, ry + 5))
        
        # Day Cycle
        ry += 15
        day_text = font.render(f"DAY: {self.state.day_number}", True, (255, 255, 255))
        self.screen.blit(day_text, (rx + 10, ry))
        
        ry += 20
        pawn_count = len(self.entity_manager.workers) + len(self.entity_manager.combat_units)
        usage_text = small_font.render(f"Upkeep: {pawn_count * 10} Food/Day", True, (255, 100, 100))
        self.screen.blit(usage_text, (rx + 10, ry))
        
        # Calculate daily yield
        food_yield = 0
        water_yield = 0
        wood_yield = 0
        ore_yield = 0
        
        for key, b_data in self.active_buildings.items():
            if b_data["type"] == "FARM":
                food_yield += 83
            elif b_data["type"] == "WELL":
                water_yield += 125
                
        if self.base_cmd_pos:
            cx, cy = self.base_cmd_pos
            min_col = max(0, int((cx - 600) // 40))
            max_col = min(self.world_cols, int((cx + 600) // 40) + 1)
            min_row = max(0, int((cy - 600) // 40))
            max_row = min(self.world_rows, int((cy + 600) // 40) + 1)
            
            for c in range(min_col, max_col):
                for r in range(min_row, max_row):
                    tile_id = self.grid[c][r]
                    if tile_id in (3, 33, 30, 34):
                        px = c * 40 + 20
                        py = r * 40 + 20
                        if math.hypot(px - cx, py - cy) <= 600:
                            if tile_id in (3, 33):
                                wood_yield += 83
                            else:
                                ore_yield += 83
                            
        ry += 20
        self.screen.blit(small_font.render("Yields/Day:", True, (200, 255, 200)), (rx + 10, ry))
        ry += 15
        self.screen.blit(small_font.render(f"Food: {int(food_yield)}", True, (200, 255, 200)), (rx + 10, ry))
        self.screen.blit(small_font.render(f"Water: {int(water_yield)}", True, (200, 255, 200)), (rx + 80, ry))
        ry += 15
        self.screen.blit(small_font.render(f"Wood: {int(wood_yield)}", True, (200, 255, 200)), (rx + 10, ry))
        self.screen.blit(small_font.render(f"Ore: {int(ore_yield)}", True, (200, 255, 200)), (rx + 80, ry))
        
        ry += 20
        bar_w = self.right_ui_width - 20
        pygame.draw.rect(self.screen, (100, 100, 100), (rx + 10, ry, bar_w, 15))
        progress = self.state.day_timer / self.state.day_duration
        color = (100, 100, 255) if self.state.is_night else (255, 200, 50) # Blue for night, yellow for day
        pygame.draw.rect(self.screen, color, (rx + 10, ry, bar_w * progress, 15))
        
        # Capacities
        ry += 30
        w_count = len(self.entity_manager.workers)
        c_count = len(self.entity_manager.combat_units)
        w_text = font.render(f"Workers: {w_count}/{self.state.max_workers}", True, (200, 255, 200))
        c_text = font.render(f"Guards: {c_count}/{self.state.max_combat}", True, (255, 200, 200))
        self.screen.blit(w_text, (rx + 10, ry))
        self.screen.blit(c_text, (rx + 10, ry + 20))

    def draw_grid(self):
        start_col = max(0, int(self.camera_x // self.cell_size))
        end_col = min(self.world_cols, int((self.camera_x + self.view_width) // self.cell_size) + 1)
        start_row = max(0, int(self.camera_y // self.cell_size))
        end_row = min(self.world_rows, int((self.camera_y + self.screen_height) // self.cell_size) + 1)
        
        scale_ratio = self.cell_size / self.logical_cell_size
        
        if self.base_cmd_pos:
            zone_radius_logical = 15 * self.logical_cell_size
            zone_radius_visual = int(zone_radius_logical * scale_ratio)
            zone_surface = pygame.Surface((zone_radius_visual*2, zone_radius_visual*2), pygame.SRCALPHA)
            pygame.draw.circle(zone_surface, (255, 255, 255, 30), (zone_radius_visual, zone_radius_visual), zone_radius_visual)
            
            vx = self.base_cmd_pos[0] * scale_ratio
            vy = self.base_cmd_pos[1] * scale_ratio
            screen_x = vx - self.camera_x + self.ui_width
            screen_y = vy - self.camera_y
            self.screen.blit(zone_surface, (screen_x - zone_radius_visual, screen_y - zone_radius_visual))
            
        for col in range(start_col, end_col):
            for row in range(start_row, end_row):
                tile_id = self.grid[col][row]
                if tile_id != 0:
                    rect = pygame.Rect(
                        self.ui_width + (col * self.cell_size - self.camera_x),
                        row * self.cell_size - self.camera_y,
                        self.cell_size,
                        self.cell_size
                    )
                    color = self.colors.get(tile_id, (255,0,255))
                    
                    # Highlight selected building
                    if self.selected_tile == (col, row):
                        pygame.draw.rect(self.screen, (255, 255, 255), rect)
                        pygame.draw.rect(self.screen, color, rect.inflate(-4, -4))
                    else:
                        pygame.draw.rect(self.screen, color, rect)
                    
                    if tile_id == 99:
                        pygame.draw.rect(self.screen, (30, 30, 30), rect, 1)
                        
                    if tile_id == 4:
                        cx = rect.x + self.cell_size
                        cy = rect.y + self.cell_size
                        aoe_radius = int(10 * self.cell_size)
                        aoe_surf = pygame.Surface((aoe_radius*2, aoe_radius*2), pygame.SRCALPHA)
                        pygame.draw.circle(aoe_surf, (255, 50, 50, 30), (aoe_radius, aoe_radius), aoe_radius)
                        self.screen.blit(aoe_surf, (cx - aoe_radius, cy - aoe_radius))
                        
                        t = pygame.time.get_ticks() / 1000.0
                        dot_x = cx + math.cos(t * 3) * (self.cell_size/2)
                        dot_y = cy + math.sin(t * 3) * (self.cell_size/2)
                        pygame.draw.circle(self.screen, (255, 200, 0), (int(dot_x), int(dot_y)), max(2, int(5*scale_ratio)))
                        
                    key = (col, row)
                    if key in self.health_map:
                        hp, max_hp = self.health_map[key]
                        if hp < max_hp:
                            bar_w = self.cell_size - 4
                            bar_h = max(2, int(4 * scale_ratio))
                            pygame.draw.rect(self.screen, (255, 0, 0), (rect.x + 2, rect.y + 2, bar_w, bar_h))
                            pygame.draw.rect(self.screen, (0, 255, 0), (rect.x + 2, rect.y + 2, bar_w * (hp / max_hp), bar_h))
                
        for col in range(start_col, end_col + 1):
            x = self.ui_width + (col * self.cell_size - self.camera_x)
            pygame.draw.line(self.screen, (50, 50, 50), (x, 0), (x, self.screen_height))
        for row in range(start_row, end_row + 1):
            y = row * self.cell_size - self.camera_y
            pygame.draw.line(self.screen, (50, 50, 50), (self.ui_width, y), (self.screen_width - self.right_ui_width, y))

    def draw(self):
        # Night dimming filter
        if self.state.is_night:
            self.screen.fill((15, 15, 20))
        else:
            self.screen.fill(self.colors[0])
            
        self.draw_grid()
        
        scale_ratio = self.cell_size / self.logical_cell_size
        self.entity_manager.draw(self.screen, self.camera_x, self.camera_y, self.ui_width, scale_ratio)
        
        self.draw_ui()
        
        if getattr(self.entity_manager, 'is_emergency', False):
            font = pygame.font.SysFont(None, 64)
            warn_text = font.render("EMERGENCY", True, (255, 0, 0))
            rect = warn_text.get_rect(center=(self.ui_width + self.view_width//2, 50))
            self.screen.blit(warn_text, rect)
        
        if self.is_paused:
            font = pygame.font.SysFont(None, 64)
            pause_text = font.render("PAUSED", True, (255, 50, 50))
            rect = pause_text.get_rect(center=(self.ui_width + self.view_width//2, self.screen_height//2))
            
            bg_rect = rect.inflate(20, 20)
            s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 150))
            self.screen.blit(s, bg_rect.topleft)
            self.screen.blit(pause_text, rect)
            
        pygame.display.flip()

    def run(self):
        while self.is_running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            
            if not self.is_paused:
                pawn_count = self.entity_manager.get_pawn_count()
                self.state.update_cycle(dt, pawn_count, self.active_buildings)
                self.entity_manager.update(dt, self.grid, self.health_map, self.active_buildings, self.state, self.world_cols, self.world_rows, self.base_cmd_pos)
                
            self.draw()
            
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    GridWorld().run()
