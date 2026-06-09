"""
MASTER DESIGN DOCUMENT

Role:
This is the root executable for the 2D base-building game. It serves as the primary 
entry point that orchestrates and launches the independent game modules.

Modular Isolation Strategy:
This file contains no game logic, rendering, or state management. It simply imports 
the top-level decoupled systems (currently the GridWorld foundation) and initiates 
the application lifecycle. Future AI agents can modify this file to inject new global 
systems, load configurations, or handle pre-launch setup without affecting the core 
gameplay code.

Core Data Structures/Specs:
- Entry point: `main()`
- Orchestrates: `GridWorld`
"""

from grid import GridWorld

def main():
    world = GridWorld()
    world.run()

if __name__ == "__main__":
    main()
