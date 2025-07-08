# render.py

import tkinter as tk
from config import (
    SCALE,
    POOL_WIDTH, POOL_HEIGHT,
    MARGIN,
    GOAL_WIDTH_M, GOAL_THICKNESS_PX,
    GOAL_ARC_RADIUS_M, PENALTY_ARC_RADIUS_M,
    PENALTY_SPOT_M,
)
from physiology import BASE_MAX_BREATH

def setup_window(game):
    """
    Create root, canvases, and draw all the static court elements:
    pool rectangle, goals, arcs, center lines, penalty spots, benches.
    """
    # 1) Root + container
    game.root = tk.Tk()
    game.root.title("Underwater Hockey")

    container = tk.Frame(game.root)
    container.pack(fill="both", expand=True)

    # 2) Main game canvas
    game.canvas_width  = int(POOL_WIDTH  * SCALE + MARGIN*2 + game.BENCH_WIDTH_PX)
    game.canvas_height = int(POOL_HEIGHT * SCALE + MARGIN*2)
    game.canvas = tk.Canvas(
        container,
        width=game.canvas_width,
        height=game.canvas_height,
        bg="white"
    )
    game.canvas.pack(side="left", fill="both", expand=True)

    # 3) Status canvas (for gauges, score, etc.)
    game.status_canvas = tk.Canvas(
        container,
        width=300,
        height=game.canvas_height,
        bg="white"
    )
    game.status_canvas.pack(side="right", fill="y")

    # Precompute boundaries
    L = MARGIN
    T = MARGIN
    R = MARGIN + POOL_WIDTH * SCALE
    B = MARGIN + POOL_HEIGHT * SCALE
    game.pool_left, game.pool_top = L, T
    game.pool_right, game.pool_bottom = R, B

    # 4) Pool rectangle
    game.canvas.create_rectangle(L, T, R, B,
        outline="black", width=2, fill="lightblue", tag="static")

    # 5) Goals (top and bottom)
    gx1 = L + (POOL_WIDTH*SCALE - GOAL_WIDTH_M*SCALE)/2
    gx2 = gx1 + GOAL_WIDTH_M * SCALE
    # top goal
    game.canvas.create_rectangle(
        gx1, T,
        gx2, T + GOAL_THICKNESS_PX,
        fill="black", outline="white", width=2,
        tag="static"
    )
    # record top goal bounds
    game.goal_x1, game.goal_x2 = gx1, gx2
    game.goal_top_y1, game.goal_top_y2 = T, T + GOAL_THICKNESS_PX

    # bottom goal
    game.canvas.create_rectangle(
        gx1, B - GOAL_THICKNESS_PX,
        gx2, B,
        fill="black", outline="white", width=2,
        tag="static"
    )
    # record bottom goal bounds
    game.goal_bottom_y1, game.goal_bottom_y2 = B - GOAL_THICKNESS_PX, B

    # 6) Goal arcs & penalty arcs
    ga_px = GOAL_ARC_RADIUS_M * SCALE
    pa_px = PENALTY_ARC_RADIUS_M * SCALE
    cx = (gx1 + gx2)/2

    # top arcs
    game.canvas.create_arc(
        cx - ga_px, T - ga_px, cx + ga_px, T + ga_px,
        start=180, extent=180, style=tk.ARC,
        outline="white", width=2, tag="static"
    )
    game.canvas.create_arc(
        cx - pa_px, T - pa_px, cx + pa_px, T + pa_px,
        start=180, extent=180, style=tk.ARC,
        outline="white", width=2, dash=(4,2), tag="static"
    )
    # bottom arcs
    game.canvas.create_arc(
        cx - ga_px, B - ga_px, cx + ga_px, B + ga_px,
        start=0, extent=180, style=tk.ARC,
        outline="white", width=2, tag="static"
    )
    game.canvas.create_arc(
        cx - pa_px, B - pa_px, cx + pa_px, B + pa_px,
        start=0, extent=180, style=tk.ARC,
        outline="white", width=2, dash=(4,2), tag="static"
    )

    # 7) Center lines & spot
    game.canvas.create_line(L, (T+B)/2, R, (T+B)/2,
        fill="white", dash=(4,2), tag="static")
    game.canvas.create_line((L+R)/2, T, (L+R)/2, B,
        fill="white", dash=(4,2), tag="static")
    spot_r = 0.3 * SCALE
    game.canvas.create_oval(
        (L+R)/2 - spot_r, (T+B)/2 - spot_r,
        (L+R)/2 + spot_r, (T+B)/2 + spot_r,
        outline="white", width=2, tag="static"
    )

    # 8) Penalty spots (top & bottom)
    ps_px = PENALTY_SPOT_M * SCALE
    for y in (T + GOAL_THICKNESS_PX + ps_px, B - GOAL_THICKNESS_PX - ps_px):
        game.canvas.create_oval(
            cx - spot_r, y - spot_r,
            cx + spot_r, y + spot_r,
            fill="white", tag="static"
        )

    # 9) Benches (just rectangles on left/right outside pool)
    bench_gap = 10
    bench_w = game.BENCH_WIDTH_PX
    # right side benches
    bx1 = R + bench_gap
    bx2 = bx1 + bench_w
    top_bench_y1 = T + 3.5 * SCALE
    game.canvas.create_rectangle(
        bx1, top_bench_y1,
        bx2, top_bench_y1 + game.BENCH_LENGTH_PX,
        outline="black", fill="lightgreen", width=2,
        tag="static"
    )
    game.canvas.create_text(
        (bx1+bx2)/2, top_bench_y1 - 10,
        text="Blue Bench", font=("Helvetica",10,"bold"),
        tag="static"
    )
    bot_bench_y2 = B - 3.5 * SCALE
    game.canvas.create_rectangle(
        bx1, bot_bench_y2 - game.BENCH_LENGTH_PX,
        bx2, bot_bench_y2,
        outline="black", fill="lightgreen", width=2,
        tag="static"
    )
    game.canvas.create_text(
        (bx1+bx2)/2, bot_bench_y2 + 10,
        text="Green Bench", font=("Helvetica",10,"bold"),
        tag="static"
    )

    # 10) Score text
    game.score_text = game.canvas.create_text(
        (L+R)/2, T - 30,
        text="Score: 0", font=("Helvetica",16,"bold"), fill="black"
    )


def update_status_bar(game):
    """Draw one gauge per green field player showing dive/stamina."""
    c = game.status_canvas
    c.delete("all")

    # collect just the 6 green field players
    green_players = [
        p for p in game.players.values()
        if p.color == "green"
    ]

    # layout constants
    gauge_w     = 30
    gauge_h     = BASE_MAX_BREATH * 10    # 10 px per second
    spacing     = 10
    start_x     = 10
    top_margin  = 20

    def time_to_y(t):
        # t=0 at bottom of gauge; t=BASE_MAX_BREATH at top
        return (top_margin + gauge_h) - (t / BASE_MAX_BREATH * gauge_h)

    for i, p in enumerate(green_players):
        x0 = start_x + i * (gauge_w + spacing)
        x1 = x0 + gauge_w
        y0 = top_margin
        y1 = y0 + gauge_h

        # border
        c.create_rectangle(x0, y0, x1, y1, outline="black")

        # effective max = min(short_term, long_term×BASE_MAX_BREATH)
        effective_max = min(p.short_term_stamina,
                            BASE_MAX_BREATH * p.long_term_stamina)
        # potential max line
        pot_y = time_to_y(BASE_MAX_BREATH * p.long_term_stamina)
        c.create_line(x0, pot_y, x1, pot_y, fill="green", width=2)

        # effective max line
        eff_y = time_to_y(effective_max)
        c.create_line(x0, eff_y, x1, eff_y, fill="blue",  width=2)

        # red fill for current dive time
        cur_y = time_to_y(p.current_dive_time)
        c.create_rectangle(x0, cur_y, x1, y1, fill="red", outline="")

        # labels
        c.create_text((x0+x1)/2, y0 - 10, text=p.label, font=("Helvetica",10))
        c.create_text((x0+x1)/2, y1 + 10,
                      text=f"{p.current_dive_time:.1f}/{effective_max:.1f}",
                      font=("Helvetica",8))