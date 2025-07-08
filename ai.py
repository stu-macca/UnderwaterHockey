# ai.py

from enum import Enum, auto
import math

class ActionType(Enum):
    SCORE_GOAL = auto()
    DEFEND     = auto()
    FORMATION  = auto()

class Action:
    def __init__(self, type: ActionType, target=None):
        self.type   = type
        self.target = target  # e.g. a (x,y) tuple for DEFEND

def decide_action(player, game):
    """
    - If this player has the puck → SCORE_GOAL
    - Elif this player is the designated chaser → DEFEND toward the puck
    - Else → FORMATION (fall back to your formation logic)
    """
    # 1) Possessor should go score
    if game.possessing_player is player:
        return Action(ActionType.SCORE_GOAL)

    # 2) Only the one chaser should chase
    if game.chaser is player:
        x1, y1, x2, y2 = game.canvas.coords(game.puck)
        puck_x = (x1 + x2) / 2
        puck_y = (y1 + y2) / 2
        return Action(ActionType.DEFEND, target=(puck_x, puck_y))

    # 3) Everyone else just slots back into formation
    return Action(ActionType.FORMATION)
