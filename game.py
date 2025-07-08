# game.py

import math
import physiology
import tkinter as tk
import render
import physics
from config import (
    SCALE,
    UPDATE_INTERVAL,
    FORMATION_THRESHOLD,
    load_formations,
    GREEN_FORMATIONS_FILE,
    BLUE_FORMATIONS_FILE,
    BENCH_LENGTH_PX,
    BENCH_WIDTH_PX,
    SPRINT_SPEED,
    PIVOT_STEP
)

from player import Player, PLAYER_RADIUS
from ai import decide_action, ActionType
from physics import compute_target_for_player
from physiology import MAX_DEPTH


class HockeyGame:
    def __init__(self):
        # -- 1) Load free‐play formations (JSON) --
        self.free_green = load_formations(GREEN_FORMATIONS_FILE)
        self.free_blue  = load_formations(BLUE_FORMATIONS_FILE)

        # Game state
        self.possessing_player = None
        self.chaser            = None
        self.score             = 0
        self.pass_hold_time     = 0.0   # seconds charged so far
        self.pass_freeze_timer  = 0.0   # seconds to freeze controlled movement
        self.pass_cooldown_timer= 0.0   # seconds before pickup allowed again
        self.game_paused       = False        # pause while “Goal!” is displayed

        # benches for render.py
        self.BENCH_LENGTH_PX = BENCH_LENGTH_PX
        self.BENCH_WIDTH_PX  = BENCH_WIDTH_PX

        # build window + static court
        render.setup_window(self)

        # keyboard
        self.keys_pressed = set()
        self.canvas.bind("<KeyPress>",   self.on_key_press)
        self.canvas.bind("<KeyRelease>", self.on_key_release)
        self.canvas.focus_set()

        # draw puck
        cx = (self.pool_left + self.pool_right)/2
        cy = (self.pool_top  + self.pool_bottom)/2
        self.puck_radius = 0.1 * SCALE
        self.puck = self.canvas.create_oval(
            cx - self.puck_radius, cy - self.puck_radius,
            cx + self.puck_radius, cy + self.puck_radius,
            fill="orange", outline="black", width=2
        )

        # create players **and record their spawn positions**
        self.players = {}
        self._create_field_players()
        self.controlled_player = self.players[1]



    def _create_field_players(self):
        import math
        # 1) Define left-to-right ordering for green (bottom) and blue (top)
        green_order = [(1, "FB"), (2, "LB"), (4, "LF"),
                       (5, "C"),  (6, "RF"), (3, "RB")]
        blue_order  = [(13, "RB"), (16, "RF"), (15, "C"),
                       (14, "LF"), (12, "LB"), (11, "FB")]

        # 2) Compute horizontal spacing and Y positions
        n = len(green_order)
        spacing  = (self.pool_right - self.pool_left) / (n - 1)
        y_green  = self.pool_bottom - PLAYER_RADIUS
        y_blue   = self.pool_top    + PLAYER_RADIUS

        # 3) Instantiate green players (facing “up”, angle=0)
        for i, (uid, label) in enumerate(green_order):
            x = self.pool_left + i * spacing
            p = Player(
                self.canvas,
                x, y_green,
                color="green",
                unique_id=uid,
                label=label,
                angle=0.0
            )
            # record spawn for resets
            p.start_x, p.start_y = x, y_green

            # initialize physiology for this player
            physiology.init_player_phys(p)

            self.players[uid] = p

        # 4) Instantiate blue players (facing “down”, angle=π)
        for i, (uid, label) in enumerate(blue_order):
            x = self.pool_left + i * spacing
            p = Player(
                self.canvas,
                x, y_blue,
                color="blue",
                unique_id=uid,
                label=label,
                angle=math.pi
            )
            p.start_x, p.start_y = x, y_blue
            physiology.init_player_phys(p)
            self.players[uid] = p

        # 5) Highlight player 1 (green FB) as the initial controlled player
        ctrl = self.players.get(1)
        if ctrl:
            self.controlled_player = ctrl
            self.canvas.itemconfig(ctrl.polygon, outline="red", width=3)




    def find_nearest_teammate_to_puck(self):
        """Return the green‐team Player (not the current controlled) closest to the puck."""
        x1, y1, x2, y2 = self.canvas.coords(self.puck)
        puck_x, puck_y = (x1 + x2) / 2, (y1 + y2) / 2

        best = None
        best_dist = float('inf')
        for p in self.players.values():
            if p.color == "green" and p is not self.controlled_player:
                d = ((p.x - puck_x)**2 + (p.y - puck_y)**2)**0.5
                if d < best_dist:
                    best_dist, best = d, p
        return best

    def switch_control(self):
        """Switch control to the green‐team teammate nearest the puck."""
        new_ctrl = self.find_nearest_teammate_to_puck()
        if not new_ctrl:
            return
        # restore old outline
        old = self.controlled_player
        if old:
            self.canvas.itemconfig(old.polygon, outline="black", width=2)
        # assign new
        self.controlled_player = new_ctrl
        # highlight new controlled in red outline
        self.canvas.itemconfig(new_ctrl.polygon, outline="red", width=3)
        # ensure they drop any AI‐chaser status
        if self.chaser is new_ctrl:
            self.chaser = None




    def on_key_press(self, event):
        # only record the key — do NOT fire passes here
        self.keys_pressed.add(event.keysym)
        if event.keysym.lower() == 'p':
            self.switch_control()

    def on_key_release(self, event):
        # if you let go of space—trigger a pass with whatever you've charged
        if (event.keysym == "space"
            and self.possessing_player is self.controlled_player
            and self.pass_hold_time > 0.0
            and self.pass_cooldown_timer <= 0.0):
            self.trigger_pass(self.pass_hold_time)

        # always drop the key
        self.keys_pressed.discard(event.keysym)




    def handle_input(self):
        """Left/Right pivots in place; Up moves forward along the current facing."""
        p = self.controlled_player
        if not p:
            return

        # 1) Pivot in place
        if "Left"  in self.keys_pressed:
            p.update_angle(p.angle - PIVOT_STEP)
        if "Right" in self.keys_pressed:
            p.update_angle(p.angle + PIVOT_STEP)

        # 2) Move forward when Up is held
        if "Up" in self.keys_pressed:
            dx = math.sin(p.angle) * SPRINT_SPEED
            dy = -math.cos(p.angle) * SPRINT_SPEED

            new_x = p.x + dx
            new_y = p.y + dy

            # clamp inside pool
            min_x = self.pool_left   + PLAYER_RADIUS
            max_x = self.pool_right  - PLAYER_RADIUS
            min_y = self.pool_top    + PLAYER_RADIUS
            max_y = self.pool_bottom - PLAYER_RADIUS

            clamped_x = max(min_x, min(max_x, new_x))
            clamped_y = max(min_y, min(max_y, new_y))

            p.update_position(clamped_x - p.x,
                              clamped_y - p.y)

    def try_pickup(self):
        """Allow the controlled player to pick up the puck if close AND sufficiently submerged."""
        # can’t pick up if someone already has it
        if self.possessing_player is not None:
            return

        p = self.controlled_player

        # must be nearly fully submerged to reach the puck on the pool bottom
        if p.depth < (MAX_DEPTH * 0.9):
            return

        # now check horizontal proximity as before
        x1, y1, x2, y2 = self.canvas.coords(self.puck)
        puck_x, puck_y = (x1 + x2) / 2, (y1 + y2) / 2
        dist = math.hypot(p.x - puck_x, p.y - puck_y)
        if dist <= PLAYER_RADIUS * 1.2:
            self.possessing_player = p

    def clamp_puck_to_player(self, player):
        """Snap the puck to the tip of the given player."""
        angle = player.angle
        tip_x = player.x + math.sin(angle) * (PLAYER_RADIUS + self.puck_radius)
        tip_y = player.y - math.cos(angle) * (PLAYER_RADIUS + self.puck_radius)
        self.canvas.coords(
            self.puck,
            tip_x - self.puck_radius, tip_y - self.puck_radius,
            tip_x + self.puck_radius, tip_y + self.puck_radius
        )

    def pick_chaser(self):
        """
        If the puck is free, pick the nearest green teammate (not you)
        as the chaser.
        """
        if self.possessing_player is not None:
            self.chaser = None
            return

        puck_coords = self.canvas.coords(self.puck)
        puck_x = (puck_coords[0] + puck_coords[2]) / 2
        puck_y = (puck_coords[1] + puck_coords[3]) / 2

        best = None
        best_d = float('inf')
        for p in self.players.values():
            if p is self.controlled_player or p.color != "green":
                continue
            d = math.hypot(p.x - puck_x, p.y - puck_y)
            if d < best_d:
                best_d, best = d, p

        self.chaser = best



    def trigger_pass(self, t: float):
        """
        t ∈ [0,1] maps linearly to a pass of 2 m → 3 m.
        Clears possession immediately so you can’t re‐pass mid‐animation.
        """
        p = self.controlled_player
        # only if you still have the puck & no cooldown
        if not p or self.pass_cooldown_timer > 0.0:
            return

        # 1) Clear possession & start timers
        self.possessing_player    = None
        self.pass_hold_time       = 0.0
        self.pass_freeze_timer    = 0.3
        self.pass_cooldown_timer  = 0.5

        # 2) Compute pass distance (meters → pixels)
        t = max(0.0, min(1.0, t))
        pass_dist_m = 2 + t           # 2 m base + up to 1 m extra = max 3 m
        dist_px     = pass_dist_m * SCALE

        angle = p.angle
        cx, cy = p.x, p.y

        # **NB** — **do not** add PLAYER_RADIUS here!
        tx = cx + math.sin(angle) * dist_px
        ty = cy - math.cos(angle) * dist_px

        # 3) Animate in 20 steps
        steps = 20
        dx = (tx - cx) / steps
        dy = (ty - cy) / steps

        def _step(i):
            if i >= steps:
                return
            self.canvas.move(self.puck, dx, dy)
            self.root.after(25, lambda: _step(i+1))

        _step(0)


    # --- Main Loop ---
    def update(self):
        # --- 0) Timers & pause/freeze ---
        dt = UPDATE_INTERVAL / 1000.0
        self.pass_freeze_timer   = max(0.0, self.pass_freeze_timer   - dt)
        self.pass_cooldown_timer = max(0.0, self.pass_cooldown_timer - dt)

        # update each player’s breath‐hold
        for p in self.players.values():
            is_ctrl     = (p is self.controlled_player)
            want_dive   = is_ctrl and ("s" in self.keys_pressed)
            physiology.update_player_breath_hold(
                p,
                UPDATE_INTERVAL/1000.0,
                is_ctrl,
                want_dive,
                canvas=self.canvas,
                puck=self.puck,
                keys_pressed=self.keys_pressed,
                controlled_player=self.controlled_player
    )

        # still paused by goal banner or frozen after a pass?
        if self.game_paused or self.pass_freeze_timer > 0.0:
            self.root.after(UPDATE_INTERVAL, self.update)
            return




        # --- 1) Human input & movement ---
        self.handle_input()

        # --- 1a) Charge & auto-fire pass on full charge ---
        if (self.possessing_player is self.controlled_player
            and "space" in self.keys_pressed
            and self.pass_cooldown_timer <= 0.0):
            self.pass_hold_time = min(1.0, self.pass_hold_time + dt)
            if self.pass_hold_time >= 1.0:
                self.trigger_pass(self.pass_hold_time)
                self.keys_pressed.discard("space")

        # --- 2) Pickup if free & off cooldown ---
        if self.pass_cooldown_timer <= 0.0:
            self.try_pickup()

        # --- 3) Carry or drop puck ---
        if self.possessing_player:
            self.clamp_puck_to_player(self.possessing_player)
            if "d" in self.keys_pressed:
                self.possessing_player = None

        # --- 4) Exactly one chaser for a loose puck ---
        self.pick_chaser()
        if self.chaser and not self.possessing_player:
            x1, y1, x2, y2 = self.canvas.coords(self.puck)
            puck_x, puck_y = (x1 + x2) / 2, (y1 + y2) / 2

            # move the chaser toward the puck
            physics.move_toward(
                self.chaser, puck_x, puck_y,
                FORMATION_THRESHOLD, self.players
            )

            # only pick up if they're down near the bottom AND within reach
            if (self.chaser.depth >= MAX_DEPTH * 0.9
                and math.hypot(self.chaser.x - puck_x,
                            self.chaser.y - puck_y)
                    <= PLAYER_RADIUS * 1.2):
                self.possessing_player = self.chaser

        # --- 5) Compute reference points ---
        x1, y1, x2, y2 = self.canvas.coords(self.puck)
        puck_cx, puck_cy = (x1 + x2)/2, (y1 + y2)/2

        # green team reference & formation name
        if self.possessing_player:
            P = self.possessing_player
            ref_x = P.x + math.sin(P.angle) * PLAYER_RADIUS
            ref_y = P.y - math.cos(P.angle) * PLAYER_RADIUS
            if   ref_x < self.pool_left  + 4*SCALE: suffix="_leftwall"
            elif ref_x > self.pool_right - 4*SCALE: suffix="_rightwall"
            else:                                   suffix=""
            green_form = f"{P.label}teammate_possession{suffix}"
        elif self.chaser:
            P = self.chaser
            ref_x = P.x + math.sin(P.angle) * PLAYER_RADIUS
            ref_y = P.y - math.cos(P.angle) * PLAYER_RADIUS
            green_form = f"{P.label}teammate_possession"
        else:
            ref_x, ref_y = puck_cx, puck_cy
            if   ref_x < self.pool_left  + 4*SCALE: green_form="left_wall"
            elif ref_x > self.pool_right - 4*SCALE: green_form="right_wall"
            else:                                   green_form="center_court"

        # blue team always free-play around puck
        if   puck_cx < self.pool_left  + 4*SCALE: blue_form="left_wall"
        elif puck_cx > self.pool_right - 4*SCALE: blue_form="right_wall"
        else:                                     blue_form="center_court"

        # debug display
        self.canvas.delete("dbg")
        self.canvas.create_text(
            self.pool_right - 80, self.pool_top + 20,
            text=f"G:{green_form}\nB:{blue_form}",
            fill="black", font=("Helvetica",12,"bold"), tag="dbg"
        )

        # --- 6) AI + formation movement for every non-controlled, non-chaser ---
        from ai import decide_action, ActionType
        for player in self.players.values():
            if player is self.controlled_player or player is self.chaser:
                continue

            action = decide_action(player, self)
            if action.type == ActionType.SCORE_GOAL:
                goal_x = (self.pool_left + self.pool_right)/2
                goal_y = (self.pool_top   + self.puck_radius
                          if player.color=="green"
                          else self.pool_bottom - self.puck_radius)
                physics.move_toward(
                    player, goal_x, goal_y,
                    FORMATION_THRESHOLD, self.players
                )
            elif action.type == ActionType.DEFEND:
                tx, ty = action.target
                physics.move_toward(
                    player, tx, ty,
                    FORMATION_THRESHOLD, self.players
                )
            else:
                # fallback into your JSON-driven formation
                if player.color == "green":
                    form_name = green_form
                    formation = self.free_green.get(green_form, {})
                    anchor_x, anchor_y = ref_x, ref_y
                else:
                    form_name = blue_form
                    formation = self.free_blue.get(blue_form, {})
                    anchor_x, anchor_y = puck_cx, puck_cy

                tx, ty = compute_target_for_player(
                    player,
                    form_name,
                    formation,
                    anchor_x, anchor_y,
                    self.pool_left, self.pool_right,
                    self.pool_top, self.pool_bottom,
                    SCALE
                )
                physics.move_toward(
                    player, tx, ty,
                    FORMATION_THRESHOLD, self.players
                )





        # --- 7) Check for goal & reset if needed ---
        self._check_goal()

        # … everything else in update() has run, right here before scheduling next frame…

        # 9) Shade each player by how deep they are
 

        # how pale at max depth: 0 = true color, 1 = full fade (toward white)
        FADE_RATIO = 0.7

        for p in self.players.values():
            # base RGB (0–255) of their team color
            r16, g16, b16 = self.canvas.winfo_rgb(p.base_color)
            r0,  g0,  b0  = r16>>8, g16>>8, b16>>8

            # precompute the “faded–white” end
            r_f = int(r0 + (255 - r0) * FADE_RATIO)
            g_f = int(g0 + (255 - g0) * FADE_RATIO)
            b_f = int(b0 + (255 - b0) * FADE_RATIO)

            # normalized “freshness”: 1.0 at surface, 0.0 at max depth
            if p is self.possessing_player:
                freshness = 1.0
            else:
                depth_norm = p.depth / MAX_DEPTH
                freshness = max(0.0, min(1.0, 1.0 - depth_norm))

            # blend: faded→true by freshness
            r = int(r_f + (r0 - r_f) * freshness)
            g = int(g_f + (g0 - g_f) * freshness)
            b = int(b_f + (b0 - b_f) * freshness)

            shade = f"#{r:02x}{g:02x}{b:02x}"
            self.canvas.itemconfig(p.polygon, fill=shade)

        # 10) redraw breath gauges:
        render.update_status_bar(self)

        # 11) Schedule next frame
        self.root.after(UPDATE_INTERVAL, self.update)




    def _check_goal(self):
        # get puck coords & center
        x1,y1,x2,y2 = self.canvas.coords(self.puck)
        cx, cy = (x1+x2)/2, (y1+y2)/2

        scored = False
        # Goal at top (green scores)
        if (x1>=self.goal_x1 and x2<=self.goal_x2 and
            y1>=self.goal_top_y1 and y2<=self.goal_top_y2) \
        or (self.goal_x1<=cx<=self.goal_x2 and
            self.goal_top_y1<=cy<=self.goal_top_y2):
            scorer = "green"
            scored = True

        # Goal at bottom (blue scores)
        if not scored and (
            x1>=self.goal_x1 and x2<=self.goal_x2 and
            y1>=self.goal_bottom_y1 and y2<=self.goal_bottom_y2
        ) or (self.goal_x1<=cx<=self.goal_x2 and
              self.goal_bottom_y1<=cy<=self.goal_bottom_y2):
            scorer = "blue"
            scored = True

        if scored:
            self.score += 1
            # update score display
            self.canvas.itemconfig(self.score_text, text=f"Score: {self.score}")
            # show banner
            self.canvas.create_text(
                (self.pool_left+self.pool_right)/2,
                self.pool_top - 40,
                text="Goal!",
                font=("Helvetica",20,"bold"),
                fill="red",
                tag="goal_msg"
            )
            # pause further updates
            self.game_paused = True
            # schedule reset
            self.root.after(3000, self._reset_after_goal)

    def _reset_after_goal(self):
        # clear banner
        self.canvas.delete("goal_msg")
        # reset puck
        cx = (self.pool_left + self.pool_right)/2
        cy = (self.pool_top  + self.pool_bottom)/2
        self.canvas.coords(
            self.puck,
            cx - self.puck_radius, cy - self.puck_radius,
            cx + self.puck_radius, cy + self.puck_radius
        )
        # reset players to their spawn
        for p in self.players.values():
            dx = p.start_x - p.x
            dy = p.start_y - p.y
            p.update_position(dx, dy)
        # clear possession & resume
        self.possessing_player = None
        self.chaser            = None
        self.game_paused       = False






    def start(self):
        self.root.after(UPDATE_INTERVAL, self.update)
        self.root.mainloop()


if __name__ == "__main__":
    game = HockeyGame()
    game.start()
