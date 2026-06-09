"""
MASTER DESIGN DOCUMENT

Role:
This module handles dynamic entities: Workers, Combat Units, and hostile Raiders.
It manages AI states including Base Zone patrolling, resource harvesting, 
day/night sleep cycles, emergency combat overrides, and raider sieges.

Modular Isolation Strategy:
Entities operate independently of Pygame's event loop. They receive spatial context 
(`grid`, `health_map`, `active_buildings`, `base_cmd_pos`) and logical context (`gamestate`) 
to update themselves each frame. `EntityManager` coordinates spawning, combat resolution, 
and emergency alarms.

Core Data Structures/Specs:
- Worker: IDLE, MOVING, WORKING, WAITING_FOR_ESCORT, HARVESTING, RETURNING, SLEEPING.
- CombatUnit: PATROL, ESCORT, COMBAT, SLEEPING. Assigned to DAY or NIGHT shifts.
- Raider: Hostile pawn spawned from Enemy Camps. Seeks and destroys.
- Emergency Alarm: If a Raider enters the Base Zone, sleeping Combat Units wake up.
"""

import math
import random
import pygame

class Worker:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 90.0
        self.state = "IDLE"
        self.target_col = -1
        self.target_row = -1
        self.build_timer = 0.0
        self.build_duration = 0.0
        self.escorts = []
        self.is_starving = False
        self.hp = 100
        self.carrying = None

    def update(self, dt, grid, health_map, active_buildings, gamestate, cols, rows, cell_size, manager, base_cmd_pos):
        self.is_starving = gamestate.starving
        speed_modifier = 0.5 if self.is_starving else 1.0
        current_speed = self.speed * speed_modifier
        
        # Sleep Override
        if gamestate.is_night:
            self.state = "SLEEPING"
            manager.release_escorts(self)
        elif self.state == "SLEEPING" and not gamestate.is_night:
            self.state = "IDLE"
            
        if self.state == "SLEEPING":
            if base_cmd_pos:
                dx = base_cmd_pos[0] - self.x
                dy = base_cmd_pos[1] - self.y
                dist = math.hypot(dx, dy)
                if dist > 20.0:
                    move_dist = min(current_speed * dt, dist)
                    self.x += (dx / dist) * move_dist
                    self.y += (dy / dist) * move_dist
            return
            
        if self.state == "IDLE":
            self._find_job(grid, health_map, active_buildings, cols, rows, manager, base_cmd_pos)
            
        elif self.state == "WAITING_FOR_ESCORT":
            if manager.assign_escorts(self):
                self.state = "MOVING"
            else:
                if base_cmd_pos:
                    self._pace_around(dt, base_cmd_pos, current_speed)

        elif self.state == "MOVING":
            target_x = self.target_col * cell_size + (cell_size / 2)
            target_y = self.target_row * cell_size + (cell_size / 2)
            
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy)
            
            if dist < 2.0:
                self.x = target_x
                self.y = target_y
                
                key = (self.target_col, self.target_row)
                blueprint_id = grid[self.target_col][self.target_row]
                
                if key in active_buildings and (active_buildings[key].get("phase") == "READY" or active_buildings[key].get("state") == "READY"):
                    self.state = "WORKING"
                    self.build_duration = 3.0
                    self.build_timer = 0.0
                elif blueprint_id in (3, 33):
                    self.state = "HARVESTING"
                    self.build_duration = 8.0
                    self.build_timer = 0.0
                elif blueprint_id in (11, 12, 14, 15, 16, 18, 19, 21):
                    self.state = "WORKING"
                    if blueprint_id == 11: self.build_duration = 5.0
                    elif blueprint_id == 12: self.build_duration = 3.0
                    elif blueprint_id == 14: self.build_duration = 15.0
                    elif blueprint_id == 15: self.build_duration = 20.0
                    elif blueprint_id == 16: self.build_duration = 12.0
                    elif blueprint_id == 18: self.build_duration = 10.0
                    elif blueprint_id == 19: self.build_duration = 10.0
                    elif blueprint_id == 21: self.build_duration = 15.0
                    self.build_timer = 0.0
                else:
                    if key in health_map and health_map[key][0] < health_map[key][1]:
                        self.state = "WORKING"
                        self.build_duration = -1.0 
                    else:
                        self.state = "IDLE"
                        manager.release_escorts(self)
            else:
                move_dist = min(current_speed * dt, dist)
                self.x += (dx / dist) * move_dist
                self.y += (dy / dist) * move_dist

        elif self.state == "WORKING":
            key = (self.target_col, self.target_row)
            tile_id = grid[self.target_col][self.target_row]
            
            if self.build_duration > 0:
                if key in active_buildings and (active_buildings[key].get("phase") == "READY" or active_buildings[key].get("state") == "READY"):
                    self.build_timer += dt
                    if self.build_timer >= self.build_duration:
                        b_data = active_buildings[key]
                        if b_data["type"] == "FARM":
                            gamestate.add("Food", 50)
                            b_data["phase"] = "SEED"
                            b_data["timer"] = 60.0
                            grid[key[0]][key[1]] = 8
                        elif b_data["type"] == "WELL":
                            gamestate.add("Water", 50)
                            b_data["state"] = "DRY"
                            b_data["timer"] = 120.0
                            grid[key[0]][key[1]] = 91
                        self.state = "IDLE"
                        manager.release_escorts(self)
                elif tile_id in (11, 12, 14, 15, 16, 18, 19, 21):
                    self.build_timer += dt
                    if self.build_timer >= self.build_duration:
                        max_hp = 100
                        if tile_id == 11: grid[self.target_col][self.target_row] = 1; max_hp = 100
                        elif tile_id == 12: grid[self.target_col][self.target_row] = 2; max_hp = 80
                        elif tile_id == 14: grid[self.target_col][self.target_row] = 4; max_hp = 300
                        elif tile_id == 15:
                            grid[self.target_col][self.target_row] = 5; max_hp = 400
                            active_buildings[key] = {"type": "BARRACKS", "level": 1}
                        elif tile_id == 21:
                            grid[self.target_col][self.target_row] = 22; max_hp = 250
                            active_buildings[key] = {"type": "CLINIC", "level": 1}
                        elif tile_id == 16: grid[self.target_col][self.target_row] = 6; max_hp = 200
                        elif tile_id == 18: 
                            grid[self.target_col][self.target_row] = 8; max_hp = 150
                            active_buildings[key] = {"type": "FARM", "phase": "SEED", "timer": 60.0}
                        elif tile_id == 19: 
                            grid[self.target_col][self.target_row] = 9; max_hp = 200
                            active_buildings[key] = {"type": "WELL", "state": "READY", "timer": 0.0}
                        
                        health_map[key] = [max_hp, max_hp]
                        self.state = "IDLE"
                        manager.release_escorts(self)
                else:
                    self.state = "IDLE"
                    manager.release_escorts(self)
            else:
                if key not in health_map:
                    self.state = "IDLE"
                    manager.release_escorts(self)
                    return
                
                health_map[key][0] += 20.0 * dt
                if health_map[key][0] >= health_map[key][1]:
                    health_map[key][0] = health_map[key][1]
                    self.state = "IDLE"
                    manager.release_escorts(self)

        elif self.state == "HARVESTING":
            tile_id = grid[self.target_col][self.target_row]
            if tile_id not in (3, 33):
                self.state = "IDLE"
                manager.release_escorts(self)
                return
                
            self.build_timer += dt
            if self.build_timer >= self.build_duration:
                grid[self.target_col][self.target_row] = 0
                is_safe = False
                if base_cmd_pos:
                    px = self.target_col * cell_size + (cell_size / 2)
                    py = self.target_row * cell_size + (cell_size / 2)
                    if math.hypot(px - base_cmd_pos[0], py - base_cmd_pos[1]) <= 600:
                        is_safe = True
                        
                manager.respawn_queue.append({
                    "col": self.target_col,
                    "row": self.target_row,
                    "timer": 180.0 if is_safe else 60.0
                })
                self.state = "RETURNING"
                
        elif self.state == "RETURNING":
            if not base_cmd_pos:
                gamestate.add("Wood", 50)
                gamestate.add("Ore", 25)
                self.state = "IDLE"
                manager.release_escorts(self)
                return
                
            dx = base_cmd_pos[0] - self.x
            dy = base_cmd_pos[1] - self.y
            dist = math.hypot(dx, dy)
            
            if dist < 40.0:
                gamestate.add("Wood", 50)
                gamestate.add("Ore", 25)
                self.state = "IDLE"
                manager.release_escorts(self)
            else:
                move_dist = min(current_speed * dt, dist)
                self.x += (dx / dist) * move_dist
                self.y += (dy / dist) * move_dist

    def _pace_around(self, dt, base_cmd_pos, current_speed):
        dx = base_cmd_pos[0] - self.x
        dy = base_cmd_pos[1] - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            tx = -dy / dist
            ty = dx / dist
            self.x += tx * current_speed * 0.5 * dt
            self.y += ty * current_speed * 0.5 * dt

    def _find_job(self, grid, health_map, active_buildings, cols, rows, manager, base_cmd_pos):
        claimed_targets = set()
        for w in manager.workers:
            if w is not self and w.state != "IDLE":
                claimed_targets.add((w.target_col, w.target_row))

        closest_dist = float('inf')
        best_col, best_row = -1, -1
        job_type = None
        
        my_col = int(self.x // 40)
        my_row = int(self.y // 40)
        
        for (c, r), b_data in active_buildings.items():
            if (b_data.get("phase") == "READY" or b_data.get("state") == "READY") and (c, r) not in claimed_targets:
                dist = math.hypot(c - my_col, r - my_row)
                if dist < closest_dist:
                    closest_dist = dist
                    best_col = c
                    best_row = r
                    job_type = "COLLECT"
                    
        if best_col == -1:
            for c in range(cols):
                for r in range(rows):
                    tile_id = grid[c][r]
                    if tile_id in (3, 33) and (c, r) not in claimed_targets:
                        is_safe = False
                        if base_cmd_pos:
                            px = c * 40 + 20
                            py = r * 40 + 20
                            if math.hypot(px - base_cmd_pos[0], py - base_cmd_pos[1]) <= 600:
                                is_safe = True
                        if tile_id == 33 or (tile_id == 3 and is_safe):
                            dist = math.hypot(c - my_col, r - my_row)
                            if dist < closest_dist:
                                closest_dist = dist
                                best_col = c
                                best_row = r
                                job_type = "HARVEST_SAFE" if is_safe else "HARVEST_RISK"
                        
        if best_col == -1:
            for c in range(cols):
                for r in range(rows):
                    if grid[c][r] in (11, 12, 14, 15, 16, 18, 19):
                        if (c, r) not in claimed_targets:
                            dist = math.hypot(c - my_col, r - my_row)
                            if dist < closest_dist:
                                closest_dist = dist
                                best_col = c
                                best_row = r
                                job_type = "BUILD"
        
        if best_col == -1:
            for (c, r), (hp, max_hp) in health_map.items():
                if hp < max_hp and (c, r) not in claimed_targets:
                    dist = math.hypot(c - my_col, r - my_row)
                    if dist < closest_dist:
                        closest_dist = dist
                        best_col = c
                        best_row = r
                        job_type = "REPAIR"

        if best_col != -1:
            self.target_col = best_col
            self.target_row = best_row
            if job_type == "HARVEST_RISK":
                self.state = "WAITING_FOR_ESCORT"
            else:
                self.state = "MOVING"

    def draw(self, surface, camera_x, camera_y, ui_offset, cell_size_ratio):
        if self.state == "SLEEPING":
            return # Don't draw sleeping workers
            
        vx = self.x * cell_size_ratio
        vy = self.y * cell_size_ratio
        screen_x = vx - camera_x + ui_offset
        screen_y = vy - camera_y
        
        if screen_x > ui_offset - 20 and screen_x < surface.get_width() + 20:
            if screen_y > -20 and screen_y < surface.get_height() + 20:
                pygame.draw.circle(surface, (255, 255, 0), (int(screen_x), int(screen_y)), int(10 * cell_size_ratio))
                
                if self.is_starving:
                    font = pygame.font.SysFont(None, int(24 * cell_size_ratio))
                    text = font.render("!", True, (255, 0, 0))
                    surface.blit(text, (screen_x - text.get_width()//2, screen_y - 25 * cell_size_ratio))
                
                if self.state in ("WORKING", "HARVESTING"):
                    bar_w = 20 * cell_size_ratio
                    bar_h = 4 * cell_size_ratio
                    bx = screen_x - bar_w / 2
                    by = screen_y - 18 * cell_size_ratio
                    pygame.draw.rect(surface, (255, 0, 0), (bx, by, bar_w, bar_h))
                    
                    if self.build_duration > 0:
                        progress = self.build_timer / self.build_duration
                        pygame.draw.rect(surface, (0, 255, 0), (bx, by, bar_w * progress, bar_h))
                    else:
                        pygame.draw.rect(surface, (0, 100, 255), (bx, by, bar_w, bar_h))

class CombatUnit:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 110.0
        self.state = "PATROL"
        self.target_worker = None
        self.patrol_target = None
        self.is_starving = False
        self.hp = 100
        self.shift = random.choice(["DAY", "NIGHT"])
        self.barracks_target = None
        
    def update(self, dt, base_cmd_pos, gamestate, manager, active_buildings):
        self.is_starving = gamestate.starving
        speed_modifier = 0.5 if self.is_starving else 1.0
        current_speed = self.speed * speed_modifier
        
        # Sleep & Emergency Override
        if manager.is_emergency:
            if self.state == "SLEEPING":
                self.state = "PATROL" # Wake up!
        else:
            is_off_shift = (gamestate.is_night and self.shift == "DAY") or (not gamestate.is_night and self.shift == "NIGHT")
            if is_off_shift and self.state not in ("ESCORT", "COMBAT"):
                self.state = "SLEEPING"
            elif not is_off_shift and self.state == "SLEEPING":
                self.state = "PATROL"
                
        if self.state == "SLEEPING":
            # Find nearest barracks
            if not self.barracks_target:
                b_dist = float('inf')
                for (c, r), b_data in active_buildings.items():
                    if b_data["type"] == "BARRACKS":
                        dist = math.hypot(c * 40 - self.x, r * 40 - self.y)
                        if dist < b_dist:
                            b_dist = dist
                            self.barracks_target = (c * 40 + 40, r * 40 + 40)
            
            if self.barracks_target:
                dx = self.barracks_target[0] - self.x
                dy = self.barracks_target[1] - self.y
                dist = math.hypot(dx, dy)
                if dist > 20.0:
                    move_dist = min(current_speed * dt, dist)
                    self.x += (dx / dist) * move_dist
                    self.y += (dy / dist) * move_dist
            return
            
        # Target Acquisition (Active Engagement)
        if self.state in ("PATROL", "COMBAT", "ESCORT"):
            best_raider = None
            closest_dist = float('inf')
            for r in manager.raiders:
                dist = math.hypot(r.x - self.x, r.y - self.y)
                if dist < closest_dist:
                    closest_dist = dist
                    best_raider = r
                    
            if best_raider and closest_dist < 400.0: # Seek within reasonable range
                self.state = "COMBAT"
                if closest_dist > 15.0:
                    dx = best_raider.x - self.x
                    dy = best_raider.y - self.y
                    move_dist = min(current_speed * dt, closest_dist)
                    self.x += (dx / closest_dist) * move_dist
                    self.y += (dy / closest_dist) * move_dist
                return
            elif self.state == "COMBAT":
                self.state = "PATROL"
            
        if self.state == "PATROL":
            if not base_cmd_pos:
                return
            
            if not self.patrol_target:
                angle = random.uniform(0, math.pi * 2)
                r = random.uniform(0, 500)
                px = base_cmd_pos[0] + math.cos(angle) * r
                py = base_cmd_pos[1] + math.sin(angle) * r
                self.patrol_target = (px, py)
                
            dx = self.patrol_target[0] - self.x
            dy = self.patrol_target[1] - self.y
            dist = math.hypot(dx, dy)
            
            if dist < 5.0:
                self.patrol_target = None
            else:
                move_dist = min(current_speed * dt * 0.5, dist)
                self.x += (dx / dist) * move_dist
                self.y += (dy / dist) * move_dist
                
        elif self.state == "ESCORT":
            if not self.target_worker or self.target_worker.state == "IDLE":
                self.state = "PATROL"
                self.target_worker = None
                return
                
            offset_x = 20
            offset_y = 20
            tx = self.target_worker.x + offset_x
            ty = self.target_worker.y + offset_y
            
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            
            if dist > 30.0:
                move_dist = min(current_speed * dt, dist)
                self.x += (dx / dist) * move_dist
                self.y += (dy / dist) * move_dist

    def draw(self, surface, camera_x, camera_y, ui_offset, cell_size_ratio):
        if self.state == "SLEEPING":
            return
            
        vx = self.x * cell_size_ratio
        vy = self.y * cell_size_ratio
        screen_x = vx - camera_x + ui_offset
        screen_y = vy - camera_y
        
        if screen_x > ui_offset - 20 and screen_x < surface.get_width() + 20:
            if screen_y > -20 and screen_y < surface.get_height() + 20:
                pygame.draw.circle(surface, (255, 100, 100), (int(screen_x), int(screen_y)), int(10 * cell_size_ratio))
                
                if self.is_starving:
                    font = pygame.font.SysFont(None, int(24 * cell_size_ratio))
                    text = font.render("!", True, (255, 0, 0))
                    surface.blit(text, (screen_x - text.get_width()//2, screen_y - 25 * cell_size_ratio))
                    
                # HP Bar
                if self.hp < 100:
                    bar_w = 20 * cell_size_ratio
                    bx = screen_x - bar_w / 2
                    by = screen_y - 15 * cell_size_ratio
                    pygame.draw.rect(surface, (255, 0, 0), (bx, by, bar_w, 4))
                    pygame.draw.rect(surface, (0, 255, 0), (bx, by, bar_w * (self.hp/100.0), 4))


class Raider:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 60.0
        self.hp = 100
        
    def update(self, dt, base_cmd_pos):
        if not base_cmd_pos: return
        dx = base_cmd_pos[0] - self.x
        dy = base_cmd_pos[1] - self.y
        dist = math.hypot(dx, dy)
        if dist > 5.0:
            self.x += (dx / dist) * self.speed * dt
            self.y += (dy / dist) * self.speed * dt
            
    def draw(self, surface, camera_x, camera_y, ui_offset, cell_size_ratio):
        vx = self.x * cell_size_ratio
        vy = self.y * cell_size_ratio
        screen_x = vx - camera_x + ui_offset
        screen_y = vy - camera_y
        if screen_x > ui_offset - 20 and screen_x < surface.get_width() + 20:
            if screen_y > -20 and screen_y < surface.get_height() + 20:
                pygame.draw.rect(surface, (150, 0, 0), (int(screen_x - 10*cell_size_ratio), int(screen_y - 10*cell_size_ratio), int(20*cell_size_ratio), int(20*cell_size_ratio)))
                if self.hp < 100:
                    bar_w = 20 * cell_size_ratio
                    bx = screen_x - bar_w / 2
                    by = screen_y - 15 * cell_size_ratio
                    pygame.draw.rect(surface, (255, 0, 0), (bx, by, bar_w, 4))
                    pygame.draw.rect(surface, (0, 255, 0), (bx, by, bar_w * (self.hp/100.0), 4))



class EntityManager:
    def __init__(self):
        self.workers = []
        self.combat_units = []
        self.medics = []
        self.raiders = []
        self.respawn_queue = []
        self.has_spawned_initial = False
        self.raider_spawn_timer = 0.0
        self.is_emergency = False
        self.debug_emergency = False

    def spawn_initial(self, px, py):
        # We don't limit initial spawn, but future spawns will be capped
        if not self.has_spawned_initial:
            for _ in range(3):
                self.workers.append(Worker(px, py))
            for _ in range(4):
                self.combat_units.append(CombatUnit(px, py))
            for _ in range(2):
                self.medics.append(Medic(px, py))
            self.has_spawned_initial = True

    def assign_escorts(self, worker):
        idle_units = [u for u in self.combat_units if u.state == "PATROL"]
        if len(idle_units) >= 2:
            escorts = idle_units[:2]
            for u in escorts:
                u.state = "ESCORT"
                u.target_worker = worker
            worker.escorts = escorts
            return True
        return False

    def release_escorts(self, worker):
        for u in worker.escorts:
            u.state = "PATROL"
            u.target_worker = None
            u.patrol_target = None
        worker.escorts = []

    def get_pawn_count(self):
        return len(self.workers) + len(self.combat_units) + len(self.medics)

    def update(self, dt, grid, health_map, active_buildings, gamestate, cols, rows, base_cmd_pos):
        cell_size = 40
        
        # Spawning logistics based on capacity limits
        if self.has_spawned_initial and base_cmd_pos:
            if len(self.workers) < gamestate.max_workers:
                self.workers.append(Worker(base_cmd_pos[0], base_cmd_pos[1]))
            if len(self.combat_units) < gamestate.max_combat:
                # Find a barracks to spawn from
                b_spawn = base_cmd_pos
                for (c, r), b_data in active_buildings.items():
                    if b_data["type"] == "BARRACKS":
                        b_spawn = (c * 40 + 40, r * 40 + 40)
                        break
                self.combat_units.append(CombatUnit(b_spawn[0], b_spawn[1]))
            if len(self.medics) < gamestate.max_medics:
                # Find a clinic to spawn from
                m_spawn = base_cmd_pos
                for (c, r), b_data in active_buildings.items():
                    if b_data["type"] == "CLINIC":
                        m_spawn = (c * 40 + 40, r * 40 + 40)
                        break
                self.medics.append(Medic(m_spawn[0], m_spawn[1]))
        
        # Respawns
        for req in self.respawn_queue[:]:
            req["timer"] -= dt
            if req["timer"] <= 0:
                grid[req["col"]][req["row"]] = 3
                self.respawn_queue.remove(req)
                
        # Active Buildings (Timers)
        for key, b_data in active_buildings.items():
            if b_data["type"] == "FARM":
                if b_data["phase"] != "READY":
                    b_data["timer"] -= dt
                    if b_data["timer"] <= 0:
                        if b_data["phase"] == "SEED":
                            b_data["phase"] = "GROW"
                            b_data["timer"] = 60.0
                            grid[key[0]][key[1]] = 81
                        elif b_data["phase"] == "GROW":
                            b_data["phase"] = "HARVEST"
                            b_data["timer"] = 60.0
                            grid[key[0]][key[1]] = 82
                        elif b_data["phase"] == "HARVEST":
                            b_data["phase"] = "READY"
                            b_data["timer"] = 0.0
                            
            elif b_data["type"] == "WELL":
                if b_data.get("state") == "DRY":
                    b_data["timer"] -= dt
                    if b_data["timer"] <= 0:
                        b_data["state"] = "READY"
                        grid[key[0]][key[1]] = 9
                        
        # Raider Spawning (Every 60s)
        self.raider_spawn_timer += dt
        if self.raider_spawn_timer >= 60.0:
            self.raider_spawn_timer = 0.0
            # Find enemy camp
            camps = []
            for c in range(cols):
                for r in range(rows):
                    if grid[c][r] == 20:
                        camps.append((c, r))
            if camps:
                spawn = random.choice(camps)
                self.raiders.append(Raider(spawn[0] * 40 + 20, spawn[1] * 40 + 20))

        # Check Emergency
        self.is_emergency = self.debug_emergency
        if base_cmd_pos and not self.is_emergency:
            for r in self.raiders:
                if math.hypot(r.x - base_cmd_pos[0], r.y - base_cmd_pos[1]) < 600:
                    self.is_emergency = True
                    break
        
        # Combat Resolution
        # Simple overlap collision combat
        for r in self.raiders:
            for c in self.combat_units:
                if math.hypot(r.x - c.x, r.y - c.y) < 30.0:
                    # Deal damage
                    r.hp -= 20.0 * dt
                    c.hp -= 15.0 * dt

        # Purge dead units
        self.raiders = [r for r in self.raiders if r.hp > 0]
        self.combat_units = [c for c in self.combat_units if c.hp > 0]
        self.workers = [w for w in self.workers if w.hp > 0] # Workers can die too if we expand combat

        # Physics / Separation
        all_pawns = self.workers + self.combat_units + self.raiders
        for i in range(len(all_pawns)):
            for j in range(i + 1, len(all_pawns)):
                p1 = all_pawns[i]
                p2 = all_pawns[j]
                dx = p1.x - p2.x
                dy = p1.y - p2.y
                dist = math.hypot(dx, dy)
                min_dist = 22.0
                
                if 0 < dist < min_dist:
                    overlap = min_dist - dist
                    push_x = (dx / dist) * (overlap / 2.0)
                    push_y = (dy / dist) * (overlap / 2.0)
                    p1.x += push_x
                    p1.y += push_y
                    p2.x -= push_x
                    p2.y -= push_y

        for w in self.workers:
            w.update(dt, grid, health_map, active_buildings, gamestate, cols, rows, cell_size, self, base_cmd_pos)
            
        for m in self.medics:
            m.update(dt, self, base_cmd_pos)
        for c in self.combat_units:
            c.update(dt, base_cmd_pos, gamestate, self, active_buildings)
            
        for r in self.raiders:
            r.update(dt, base_cmd_pos)

    def draw(self, surface, camera_x, camera_y, ui_offset, cell_size_ratio):
        for w in self.workers:
            w.draw(surface, camera_x, camera_y, ui_offset, cell_size_ratio)
        for m in self.medics:
            m.draw(surface, camera_x, camera_y, ui_offset, cell_size_ratio)
        for c in self.combat_units:
            c.draw(surface, camera_x, camera_y, ui_offset, cell_size_ratio)
        for r in self.raiders:
            r.draw(surface, camera_x, camera_y, ui_offset, cell_size_ratio)

class Medic:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 100.0
        self.state = "IDLE"
        self.target = None
        self.hp = 100

    def update(self, dt, manager, base_cmd_pos):
        if self.state == "IDLE":
            # Find a target to heal
            best_target = None
            best_dist = float('inf')

            for w in manager.workers:
                if w.hp < 100:
                    dist = math.hypot(w.x - self.x, w.y - self.y)
                    if dist < best_dist:
                        best_dist = dist
                        best_target = w

            for c in manager.combat_units:
                if c.hp < 100:
                    dist = math.hypot(c.x - self.x, c.y - self.y)
                    if dist < best_dist:
                        best_dist = dist
                        best_target = c

            if best_target:
                self.target = best_target
                self.state = "HEALING"
            else:
                # Wander around base
                if base_cmd_pos:
                    dx = base_cmd_pos[0] - self.x
                    dy = base_cmd_pos[1] - self.y
                    dist = math.hypot(dx, dy)
                    if dist > 150.0:
                        self.x += (dx / dist) * self.speed * dt
                        self.y += (dy / dist) * self.speed * dt
                    else:
                        # random wander
                        self.x += random.uniform(-1, 1) * self.speed * dt
                        self.y += random.uniform(-1, 1) * self.speed * dt

        elif self.state == "HEALING":
            if not self.target or self.target.hp >= 100:
                self.state = "IDLE"
                self.target = None
                return

            dx = self.target.x - self.x
            dy = self.target.y - self.y
            dist = math.hypot(dx, dy)

            if dist > 10.0:
                self.x += (dx / dist) * self.speed * dt
                self.y += (dy / dist) * self.speed * dt
            else:
                # Heal
                self.target.hp = min(100, self.target.hp + 20.0 * dt)

    def draw(self, surface, camera_x, camera_y, ui_offset, cell_size_ratio):
        vx = self.x * cell_size_ratio
        vy = self.y * cell_size_ratio
        screen_x = vx - camera_x + ui_offset
        screen_y = vy - camera_y

        if screen_x > ui_offset - 20 and screen_x < surface.get_width() + 20:
            if screen_y > -20 and screen_y < surface.get_height() + 20:
                pygame.draw.circle(surface, (0, 255, 255), (int(screen_x), int(screen_y)), int(10 * cell_size_ratio))

                if self.hp < 100:
                    bar_w = 20 * cell_size_ratio
                    bx = screen_x - bar_w / 2
                    by = screen_y - 15 * cell_size_ratio
                    pygame.draw.rect(surface, (255, 0, 0), (bx, by, bar_w, 4))
                    pygame.draw.rect(surface, (0, 255, 0), (bx, by, bar_w * (self.hp/100.0), 4))
