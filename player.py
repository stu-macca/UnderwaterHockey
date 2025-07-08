# player.py

import math
import tkinter as tk
from config import SCALE

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------
# Radius of the triangular player in pixels
PLAYER_RADIUS = (1.82 * SCALE) / 1.5

# -------------------------------------------------------------------
# Player Class
# -------------------------------------------------------------------
class Player:
    """
    Represents a single player as a colored triangle with a label.
    """

    def __init__(
        self,
        canvas: tk.Canvas,
        x: float,
        y: float,
        color: str,
        unique_id: int,
        label: str,
        angle: float = 0.0,
    ):
        # Canvas & identity
        self.canvas = canvas
        self.unique_id = unique_id
        self.label = label

        # Visual state
        self.x = x
        self.y = y
        self.angle = angle
        self.base_color = color
        self.color = color


        # Depth (for collision checks); 0 = surface
        self.depth = 0.0

        # Canvas items (created on first draw)
        self.polygon = None
        self.text = None

        # Initial draw
        self.draw()

    def draw(self):
        """Draw or update the triangle and its label."""
        R = PLAYER_RADIUS
        fx = math.sin(self.angle)
        fy = -math.cos(self.angle)
        rx = math.cos(self.angle)
        ry = math.sin(self.angle)

        # Compute triangle vertices
        tip = (
            self.x + R * fx,
            self.y + R * fy
        )
        base_left = (
            self.x - (R / 4) * fx + (R / 4) * rx,
            self.y - (R / 4) * fy + (R / 4) * ry
        )
        base_right = (
            self.x - (R / 4) * fx - (R / 4) * rx,
            self.y - (R / 4) * fy - (R / 4) * ry
        )
        points = (*tip, *base_left, *base_right)

        if self.polygon:
            # Update existing
            self.canvas.coords(self.polygon, *points)
            self.canvas.itemconfig(self.polygon, fill=self.color)
            self.canvas.coords(self.text, self.x, self.y)
            self.canvas.itemconfig(self.text, text=self.label)
        else:
            # Create new
            self.polygon = self.canvas.create_polygon(
                points, fill=self.color, outline="black", width=2
            )
            self.text = self.canvas.create_text(
                self.x, self.y, text=self.label,
                font=("Helvetica", 12, "bold"), fill="white"
            )

    def update_position(self, dx: float, dy: float):
        """Move the player by (dx, dy) in canvas coordinates."""
        self.x += dx
        self.y += dy
        self.canvas.move(self.polygon, dx, dy)
        self.canvas.move(self.text, dx, dy)

    def update_angle(self, new_angle: float):
        """Rotate the player to `new_angle` (in radians) and redraw."""
        self.angle = new_angle
        self.draw()

    def update_color(self, new_color: str):
        """Change the player's fill color."""
        self.color = new_color
        if self.polygon:
            self.canvas.itemconfig(self.polygon, fill=new_color)


# -------------------------------------------------------------------
# Helper: Triangle Vertices
# -------------------------------------------------------------------
def get_triangle_vertices(player, center_x=None, center_y=None, angle=None):
    """
    Return the three (x,y) vertices of a player's triangle, matching `draw()`.

    If center_x/center_y/angle are omitted, uses the player's current state.
    """
    if center_x is None:
        center_x = player.x
    if center_y is None:
        center_y = player.y
    if angle is None:
        angle = player.angle

    R = PLAYER_RADIUS
    fx = math.sin(angle)
    fy = -math.cos(angle)
    rx = math.cos(angle)
    ry = math.sin(angle)

    tip = (
        center_x + R * fx,
        center_y + R * fy
    )
    bl = (
        center_x - (R / 2) * fx + (R / 2) * rx,
        center_y - (R / 2) * fy + (R / 2) * ry
    )
    br = (
        center_x - (R / 2) * fx - (R / 2) * rx,
        center_y - (R / 2) * fy - (R / 2) * ry
    )

    return [tip, bl, br]
