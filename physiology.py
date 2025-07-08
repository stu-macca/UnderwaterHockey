# physiology.py

import random
import math

# Constants (you can hoist some of these into config.py if you like)
MAX_DEPTH               = 2.0               # meters
DEPTH_STEP              = 0.1               # m per frame
BASE_MAX_BREATH         = 20.0              # seconds at long_term_stamina=1
SHORT_TERM_REGEN_RATE   = 0.2               # sec recovered per sec on surface
LONG_TERM_PENALTY_RATE  = 0.02              # fraction lost per full dive
EXTRA_DIVE_PENALTY_FACTOR = 1.5
MIN_SHORT_TERM           = 5.0
MIN_LONG_TERM            = 0.5
SURFACE_LOCK_DURATION    = 3.0               # seconds

def init_player_phys(player):
    """Call once when you create each Player."""
    player.depth              = 0.0
    player.submerging         = False
    player.current_dive_time  = 0.0
    player.short_term_stamina = BASE_MAX_BREATH
    player.long_term_stamina  = 1.0
    player.surface_lock_timer = 0.0
    player.dive_threshold     = None  # assigned later for AI

def update_player_breath_hold(player,
                              dt: float,
                              is_controlled: bool,
                              want_to_dive: bool,
                              canvas=None,
                              puck=None,
                              keys_pressed=None,
                              controlled_player=None):
    """
    - dt: seconds since last frame
    - is_controlled: True if user is controlling this player
    - want_to_dive: for controlled only, True if 's' held
    - canvas, puck, keys_pressed, controlled_player only needed for AI logic
    """

    # 1) Bench players (if you ever tag one with player.role="bench")
    if getattr(player, "role", "field") == "bench":
        return

    # 2) Surface‐lock countdown: force surfaced while >0
    if player.surface_lock_timer > 0:
        player.surface_lock_timer = max(0.0, player.surface_lock_timer - dt)
        player.submerging = False
    else:
        # 3) Decide submerging
        if is_controlled:
            # user: dive only while holding 's' and have breath
            player.submerging = want_to_dive and player.short_term_stamina > 0
        else:
            # AI: dive if near puck (and have breath)
            # must pass in canvas, puck, etc. into this call
            if canvas is None or puck is None:
                raise RuntimeError("AI breath logic needs canvas & puck")
            x1,y1,x2,y2 = canvas.coords(puck)
            puck_x, puck_y = (x1+x2)/2, (y1+y2)/2
            dist = math.hypot(player.x - puck_x, player.y - puck_y)
            player.submerging = dist < 150 and player.short_term_stamina > 0

            # if starting a new dive, give them a random threshold
            if player.submerging and (player.dive_threshold is None or player.current_dive_time == 0):
                player.dive_threshold = random.uniform(6, 14)

    # 4) If submerging → descend & deplete breath
    if player.submerging:
        player.current_dive_time += dt
        player.depth = min(MAX_DEPTH, player.depth + DEPTH_STEP)
        player.short_term_stamina = max(0.0, player.short_term_stamina - dt)

        # decide threshold: user uses their effective_max, AI uses own threshold
        if is_controlled:
            threshold = min(player.short_term_stamina,
                            BASE_MAX_BREATH * player.long_term_stamina)
        else:
            threshold = player.dive_threshold

        if player.current_dive_time >= threshold:
            # force them to surface
            player.submerging = False
            player.surface_lock_timer = SURFACE_LOCK_DURATION
            if not is_controlled:
                # re-roll for next AI dive
                player.dive_threshold = random.uniform(6, 14)

    else:
        # 5) Surfacing behaviour
        # float upward
        player.depth = max(0.0, player.depth - DEPTH_STEP)

        # if just surfaced fully after a dive
        if player.depth == 0.0 and player.current_dive_time > 0:
            # extra‐dive penalty
            if player.current_dive_time > 10:
                penalty = (player.current_dive_time - 10) * EXTRA_DIVE_PENALTY_FACTOR
            else:
                penalty = (player.current_dive_time / 10) * EXTRA_DIVE_PENALTY_FACTOR

            player.short_term_stamina = max(
                MIN_SHORT_TERM,
                player.short_term_stamina - penalty
            )
            player.long_term_stamina = max(
                MIN_LONG_TERM,
                player.long_term_stamina - 
                  LONG_TERM_PENALTY_RATE * (player.current_dive_time / BASE_MAX_BREATH)
            )
            player.current_dive_time = 0.0

        # regen short‐term up to new potential max
        potential_max = BASE_MAX_BREATH * player.long_term_stamina
        player.short_term_stamina = min(
            potential_max,
            player.short_term_stamina + SHORT_TERM_REGEN_RATE * dt
        )

    # 6) (Optional) update their color/shading if you want here,
    #     or call player.update_color() back in game.update()
    if hasattr(player, "update_color"):
        player.update_color(player.color)
