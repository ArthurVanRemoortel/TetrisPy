from pprint import pprint
from typing import Optional

from kivy.uix.button import Button
import random
from itertools import cycle

from kivy.uix.label import Label
from kivy.uix.widget import Widget

from constants import *
from helpers import Position, Direction, RootAccess
from kivy.properties import *
import copy
from enum import Enum


class BrickShape(object):
    def __init__(self, shape_template):
        self.shape_template: [[int]] = shape_template
        self._current_rotation = 0

    @classmethod
    def random_shape(cls) -> 'BrickShape':
        return BrickShape(random.choice(SHAPE_TEMPLATES))

    def rotate(self):
        self._current_rotation = (self._current_rotation + 1) % len(self.shape_template)

    def current_rotation_shape(self):
        return self.shape_template[self._current_rotation]

    @classmethod
    def get_shape(cls, i) -> 'BrickShape':
        """ for dev only. """
        return BrickShape(SHAPE_TEMPLATES[i])

    @classmethod
    def get_single_block_brick_shape(cls):
        """ used to simply color a block some color """
        return BrickShape([[[0, 0]]])


class TetrisBlockWidget(Label):
    padding: int = NumericProperty(2)
    occupied_by: 'TetrisBrick' = ObjectProperty(None, allownone=True)
    position: Position = ObjectProperty(None)

    def __init__(self, game_field, position: Position):
        """
        Correspond to a single block, like a pixel, that can light up.
        :param game_field: Part of the GUI where the game is rendered.
        :param position: Coordinate of the block in the field.
        """
        super(TetrisBlockWidget, self).__init__()
        self.game_field: 'GameField' = game_field
        self.position: Position = position

    def __str__(self):
        return f'TetrisBlockWidget at position ({self.position})'


class TetrisBrick(Widget, RootAccess):
    game_field:       'GameField'          = ObjectProperty(None)
    position:         Position             = ObjectProperty(None)
    occupied_blocks:  [TetrisBlockWidget]  = ListProperty([])
    color:            [float]              = ListProperty([1, 0, 0, .5])
    shape:            BrickShape           = ObjectProperty(None)

    def __init__(self, game_field: 'GameField', position: Position, shape: BrickShape = None, init_color = None):
        """
        A tetris brick that will be rendered by the GUI framework.
        :param game_field: Part of the GUI where the game is rendered.
        :param position: Position where the block will be created.
        :param shape: Initialize a brick with a specific shape. Random shape if not specified.
        """
        super(TetrisBrick, self).__init__()
        self.game_field = game_field
        self.position = position
        self.color = random.choice(COLORS) if init_color is None else init_color
        self.shape = shape
        if self.shape is None:
            self.shape = BrickShape.random_shape()
        self.update_occupied_blocks()

    def move(self, direction: Direction):
        """
        Moves this brick 1 block in the provided direction.
        GUI will automatically me updated.
        :param direction: Direction.LEFT, Direction.RIGHT or Direction.DOWN.
        """
        if self.can_brick_move_to(direction=direction):
            self.position.add_offset(direction.to_position_offset())
            self.update_occupied_blocks()
        else:
            if direction is Direction.DOWN:
                if self.is_game_over():
                    self.app_root.game_over()
                else:
                    self.game_field.clear_full_rows()
                    self.game_field.select_next_brick()

    def is_game_over(self) -> bool:
        """
        Detects if the brick is causing the game to end. Should only be called if brick is currently moving down.
        :return: true if game should end for this player.
        """
        return self.position.y == 0

    def can_brick_move_to(self, direction: Direction) -> bool:
        next_positions = map(lambda occupied_block: occupied_block.position.next(direction=direction), self.occupied_blocks)
        return self.are_positions_valid(next_positions)

    def are_positions_valid(self, positions: [Position], ignore: list[Position] = None) -> bool:
        """
        :param positions: List of positions to be checked.
        :param ignore: List of positions that collision check can ignore. Usually a temporary dummy brick.
        :return: All positions are valid.
        """
        if ignore is None:
            ignore = []
        ignore.append(self)  # Ignores collision with itself.
        for position in positions:
            block_widget: TetrisBlockWidget = self.game_field.get_block_widget(position)
            if block_widget is None or (block_widget.occupied_by not in ignore and self and block_widget.occupied_by is not None):
                # block_widget is None: Block does not exist. Happens when a position is out of bounds.
                # block_widget.occupied_by is not in ignored: current brick collides with another brick that it is not allowed to collide with.
                #     It's  allowed to collide with either itself or a dummy brick copied from itself.
                return False
        return True

    def update_occupied_blocks(self):
        """
        Updates the bricks knowledge about which positions it occupies.
        Updates the blocks knowledge about which brick its occupied by.
        Automatically updates the GUI too.
        """
        occupied_blocks_before = set(self.occupied_blocks)
        self.occupied_blocks = []
        for block in self.game_field.map_brick_shape_to_blocks(brick_shape=self.shape, position=self.position):
            self.occupied_blocks.append(block)
            block.occupied_by = self

        no_longer_occupied_blocks = occupied_blocks_before.difference(set(self.occupied_blocks))
        for block in no_longer_occupied_blocks:
            block.occupied_by = None

    def rotate(self):
        """
        Rotates this brick by creating a copy of this brick, rotating it and checking if the copy is valid before copying the original.
        """
        dummy_shape = copy.deepcopy(self.shape)
        dummy_shape.rotate()
        field_blocks = self.game_field.map_brick_shape_to_blocks(brick_shape=dummy_shape, position=self.position)
        if None in field_blocks:
            # At least one position maps to an no existent block.
            return
        if self.are_positions_valid(
                positions=map(lambda block: block.position, self.game_field.map_brick_shape_to_blocks(brick_shape=dummy_shape, position=self.position)),
                ignore=[dummy_shape]):
            # ignore=[dummy_shape] because the current brick should not check if it collides with the dummy shape, which is a rotated copy of itself.
            self.shape.rotate()
            self.update_occupied_blocks()


