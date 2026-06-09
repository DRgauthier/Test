"""
MASTER DESIGN DOCUMENT

Role:
This module acts as the central ledger for the game's economy, player progress, and time.
It tracks global resources, day/night cycles, hunger mechanics, and pawn capacity limits.

Modular Isolation Strategy:
A completely standalone module that stores state. It is injected or imported 
wherever economic transactions or UI reads are necessary, keeping the economy logic 
decoupled from the grid and the entities.

Core Data Structures/Specs:
- `resources`: Dictionary tracking Wood, Food, Water, Ore.
- `day_duration`: 300 seconds (200s Day, 100s Night).
- `is_night`: Boolean for entities to govern sleep cycles.
- `capacities`: Max workers and combat units calculated dynamically from buildings.
"""

class GameState:
    def __init__(self):
        self.resources = {
            "Wood": 500,
            "Food": 200,
            "Water": 200,
            "Ore": 100
        }
        self.day_number = 1
        self.day_duration = 300.0  # 5 minutes
        self.day_timer = 0.0
        self.is_night = False
        self.starving = False
        
        self.max_workers = 0
        self.max_combat = 0

    def update_cycle(self, dt, pawn_count, active_buildings):
        self.day_timer += dt
        
        # Day is first 200s, Night is last 100s
        self.is_night = self.day_timer >= 200.0
        
        if self.day_timer >= self.day_duration:
            self.day_timer = 0.0
            self.day_number += 1
            
            # Consume food at dawn
            food_needed = pawn_count * 10
            if self.resources.get("Food", 0) >= food_needed:
                self.resources["Food"] -= food_needed
                self.starving = False
            else:
                self.resources["Food"] = 0
                self.starving = True
                
        # Recalculate capacities dynamically based on active buildings
        w_cap = 0
        c_cap = 0
        for key, b_data in active_buildings.items():
            lvl = b_data.get("level", 1)
            if b_data["type"] == "COMMAND":
                w_cap += (3 + (lvl - 1) * 2) # Lv1: 3, Lv2: 5, Lv3: 7
                c_cap += (2 + (lvl - 1) * 2) # Base Command provides 2 guards at Lv1
            elif b_data["type"] == "BARRACKS":
                c_cap += (4 + (lvl - 1) * 4) # Lv1: 4, Lv2: 8, Lv3: 12
                
        self.max_workers = w_cap
        self.max_combat = c_cap

    def can_afford(self, costs):
        for res, amount in costs.items():
            if self.resources.get(res, 0) < amount:
                return False
        return True

    def deduct(self, costs):
        if self.can_afford(costs):
            for res, amount in costs.items():
                self.resources[res] -= amount
            return True
        return False
        
    def add(self, resource, amount):
        if resource in self.resources:
            self.resources[resource] += amount
