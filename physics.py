# physics.py
import random
import math
from config import COLLISION_DEPTH_THRESHOLD, FORMATION_THRESHOLD, PIVOT_STEP, SPRINT_SPEED
from player import PLAYER_RADIUS
from player import get_triangle_vertices
from config import SPRINT_SPEED



def project_polygon(polygon, axis):
    """Projects all vertices onto the given normalized axis."""
    projections = [v[0]*axis[0] + v[1]*axis[1] for v in polygon]
    return min(projections), max(projections)

def polygons_collide(poly1, poly2, epsilon=1.5):
    """
    SAT collision check with margin (epsilon). Returns True if polygons collide.
    Allows slight overlap to avoid jitter/sticking.
    """
    for polygon in (poly1, poly2):
        n = len(polygon)
        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]
            edge = (p2[0] - p1[0], p2[1] - p1[1])
            axis = (-edge[1], edge[0])
            length = math.hypot(*axis)
            if length == 0:
                continue
            axis = (axis[0] / length, axis[1] / length)
            min1, max1 = project_polygon(poly1, axis)
            min2, max2 = project_polygon(poly2, axis)

            # Allow slight overlap using epsilon margin
            if max1 < min2 - epsilon or max2 < min1 - epsilon:
                return False
    return True

def is_collision(player, new_x, new_y, all_players):
    """
    Returns True if moving `player` to (new_x,new_y) collides
    with any other player at similar depth.
    """
    from player import get_triangle_vertices

    tri1 = get_triangle_vertices(player, center_x=new_x, center_y=new_y, angle=player.angle)
    for other in all_players.values():
        if other is player:
            continue
        if abs(other.depth - player.depth) >= COLLISION_DEPTH_THRESHOLD:
            continue
        tri2 = get_triangle_vertices(other)
        if polygons_collide(tri1, tri2, epsilon=1.5):
            return True
    return False

def move_toward(player, tx, ty, threshold, all_players):
    """
    Pivot toward (tx, ty), then move forward if no collision.
    If blocked, try sidestepping. If still blocked, try alternate nearby targets.
    """
    dx = tx - player.x
    dy = ty - player.y
    dist = math.hypot(dx, dy)

    if dist < threshold:
        return

    desired = math.atan2(dy, dx) + math.pi / 2
    diff = (desired - player.angle + math.pi) % (2 * math.pi) - math.pi
    turn = max(-PIVOT_STEP, min(PIVOT_STEP, diff))
    new_angle = player.angle + turn
    player.update_angle(new_angle)

    step = min(SPRINT_SPEED, dist)
    fx = math.sin(player.angle)
    fy = -math.cos(player.angle)

    new_x = player.x + fx * step
    new_y = player.y + fy * step

    if not is_collision(player, new_x, new_y, all_players):
        player.update_position(fx * step, fy * step)
        return

    # Try sidestepping ±15°, ±30°, ±45°
    for sidestep_deg in [15, -15, 30, -30, 45, -45]:
        offset = math.radians(sidestep_deg)
        sidestep_angle = player.angle + offset
        sidestep_dx = math.sin(sidestep_angle) * step
        sidestep_dy = -math.cos(sidestep_angle) * step
        sidestep_x = player.x + sidestep_dx
        sidestep_y = player.y + sidestep_dy

        if not is_collision(player, sidestep_x, sidestep_y, all_players):
            player.update_angle(sidestep_angle)
            player.update_position(sidestep_dx, sidestep_dy)
            return

    # --- Fallback: try nearby clear positions as temporary targets ---
    fallback_radius = PLAYER_RADIUS * 2
    fallback_attempts = 6
    for _ in range(fallback_attempts):
        angle = random.uniform(0, 2 * math.pi)
        alt_x = player.x + math.cos(angle) * fallback_radius
        alt_y = player.y + math.sin(angle) * fallback_radius

        alt_dx = alt_x - player.x
        alt_dy = alt_y - player.y
        alt_dist = math.hypot(alt_dx, alt_dy)
        if alt_dist < 1e-3:
            continue

        alt_angle = math.atan2(alt_dy, alt_dx) + math.pi / 2
        fx = math.sin(alt_angle)
        fy = -math.cos(alt_angle)
        step = min(SPRINT_SPEED, alt_dist)

        trial_x = player.x + fx * step
        trial_y = player.y + fy * step

        if not is_collision(player, trial_x, trial_y, all_players):
            player.update_angle(alt_angle)
            player.update_position(fx * step, fy * step)
            return

    # Still stuck? final fallback — small random nudge
    player.update_angle(player.angle + random.uniform(-0.05, 0.05))

def compute_target_for_player(
    player,
    formation_name,
    formation,
    ref_x, ref_y,
    pool_left, pool_right,
    pool_top, pool_bottom,
    SCALE
):
    import math
    from player import PLAYER_RADIUS

    def get_offside_back_position(player, ref_x, ref_y, defending_side):
        goal_center_x = (pool_left + pool_right) / 2
        goal_center_y = pool_bottom if defending_side == "bottom" else pool_top
        vec_x, vec_y = goal_center_x - ref_x, goal_center_y - ref_y
        norm = math.hypot(vec_x, vec_y)
        if norm == 0:
            return ref_x, ref_y
        # push 3*radius behind the offside line
        return (
            ref_x + (5 * PLAYER_RADIUS / norm) * vec_x,
            ref_y + (5 * PLAYER_RADIUS / norm) * vec_y
        )

    # --- 1) Offside‐backs (only the single back on the wrong side) ---
    if "leftwall" in formation_name:
        # on left wall we only offside the back furthest from the wall
        if player.color=="green" and player.label=="RB":
            return get_offside_back_position(player, ref_x, ref_y, "bottom")
        if player.color=="blue"  and player.label=="LB":
            return get_offside_back_position(player, ref_x, ref_y, "top")

    elif "rightwall" in formation_name:
        # on right wall we only offside the back furthest from the wall
        if player.color=="green" and player.label=="LB":
            return get_offside_back_position(player, ref_x, ref_y, "bottom")
        if player.color=="blue"  and player.label=="RB":
            return get_offside_back_position(player, ref_x, ref_y, "top")

    # --- 2) Everyone else (forwards, center, the other back) just follow JSON offsets ---
    # Ensure the label exists in this formation
    if player.label not in formation:
        # no entry → hold current spot
        return player.x, player.y

    offset_x_m, offset_y_m = formation[player.label]
    tx = ref_x + offset_x_m * SCALE
    ty = ref_y + offset_y_m * SCALE

    # --- 3) Clamp inside pool bounds (so no one ever swims out) ---
    tx = max(pool_left  + PLAYER_RADIUS, min(pool_right  - PLAYER_RADIUS, tx))
    ty = max(pool_top   + PLAYER_RADIUS, min(pool_bottom - PLAYER_RADIUS, ty))

    return tx, ty
