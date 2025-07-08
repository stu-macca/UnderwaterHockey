# config.py

import json
import os

# --------------------
# Paths
# --------------------
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
GREEN_FORMATIONS_FILE = os.path.join(DATA_DIR, "green_formations.json")
BLUE_FORMATIONS_FILE  = os.path.join(DATA_DIR, "blue_formations.json")

# --------------------
# JSON Loader
# --------------------
def load_formations(path: str) -> dict:
    """
    Load formations from a JSON file and return a dict:
      formation_name → { role_label: [x_offset, y_offset], … }
    """
    with open(path, 'r') as f:
        return json.load(f)

# --------------------
# Timing & Scaling
# --------------------
SCALE                   = 25       # pixels per meter
UPDATE_INTERVAL         = 50       # ms between frames
FORMATION_THRESHOLD     = 3        # px tolerance for formation alignment

# --------------------
# Player & Physics
# --------------------
SPRINT_SPEED_FACTOR         = 0.05    # fraction of pool height per frame
SPRINT_SPEED                = 3.125   # px/frame when sprinting
MAX_DEPTH                   = 2.0     # maximum dive depth (m)
DEPTH_STEP                  = 0.1     # m per frame for dive/resurface
PASS_FREEZE                 = 0.3     # s freeze after a pass
COLLISION_DEPTH_THRESHOLD   = 0.4     # m difference for collision check

# radians per update when pivoting
PIVOT_STEP               = 0.45

# --------------------
# Pool Dimensions (meters)
# --------------------
POOL_WIDTH   = 15       # horizontal length (m)
POOL_HEIGHT  = 25       # vertical length (m)
MARGIN       = 25       # px around the pool

# --------------------
# Goal & Arc Dimensions
# --------------------
GOAL_WIDTH_M         = 3        # m
GOAL_WIDTH_PX        = GOAL_WIDTH_M * SCALE
GOAL_THICKNESS_PX    = 10       # px
GOAL_ARC_RADIUS_M    = 2        # m
PENALTY_ARC_RADIUS_M = 3        # m
PENALTY_SPOT_M       = 6        # m

# --------------------
# Bench Dimensions
# --------------------
BENCH_LENGTH_M  = 5           # m
BENCH_LENGTH_PX = BENCH_LENGTH_M * SCALE
BENCH_OFFSET_M  = 3.5         # m from pool edge
BENCH_OFFSET_PX = BENCH_OFFSET_M * SCALE
BENCH_WIDTH_PX  = int((POOL_WIDTH * SCALE) / 4)  # e.g., a quarter of pool width

# --------------------
# Physiology & Dive Settings
# --------------------
BASE_MAX_BREATH           = 20.0    # seconds of ideal breath‐hold
SHORT_TERM_REGEN_RATE     = 0.2     # seconds of stamina recovered per second on surface
LONG_TERM_PENALTY_RATE    = 0.02    # permanent reduction per dive fraction
EXTRA_DIVE_PENALTY_FACTOR = 1.5     # extra penalty per second beyond 10s
MIN_SHORT_TERM            = 5.0     # minimum short‐term stamina (seconds)
MIN_LONG_TERM             = 0.5     # minimum long‐term multiplier

SURFACE_LOCK_DURATION     = 3.0     # seconds before a player can dive again after surfacing
AI_DIVE_RANGE             = 150.0   # px: distance within which AI will choose to dive
