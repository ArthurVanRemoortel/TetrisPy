import copy
from pprint import pprint
from threading import Thread
from typing import Optional

import numpy
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.properties import *
from kivy.core.window import Window as CoreWindow, Window
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from gui.popups import LobbyPopup, LobbyRow
from helpers import RootAccess, Position, Direction, GameLobby, Player
from tetris.tetris_block import TetrisBlockWidget, BrickShape, TetrisBrick
from collections import deque
from constants import *
from firebase_connection import FirebaseConnection, FIREBASE_CONNECTION
from PodSixNet.Connection import ConnectionListener, connection


class GameField(BoxLayout, RootAccess):
    blocks: [[TetrisBlockWidget]] = ListProperty([])
    current_brick: TetrisBrick = ObjectProperty(None)
    brick_shapes_queue = deque()
    player = ObjectProperty(None)
    game_over: bool = BooleanProperty(False)
    score: int = NumericProperty(0)
    # changes_tracker: GameFieldChangesTracker = GameFieldChangesTracker()

    def __init__(self, player, **kwargs):
        super(GameField, self).__init__()
        self.bind(size=self.resize_height)
        self.player = player
        self.field_grid: BoxLayout = self.ids.field_grid
        self.field_grid.cols = TETRIS_BOARD_COLS
        self.field_grid.rows = TETRIS_BOARD_ROWS
        for row in range(TETRIS_BOARD_ROWS):
            self.blocks.append([])
            for col in range(TETRIS_BOARD_COLS):
                pos = Position(x=col, y=row)
                block_wid = TetrisBlockWidget(game_field=self, position=pos)
                self.blocks[row].append(block_wid)
                self.field_grid.add_widget(block_wid)

        if self.player.local:
            self.set_brick_queue()

    def set_brick_queue(self, bricks=None):
        if bricks is None:
            for i in range(2):
                self.brick_shapes_queue.append(self.create_brick_shape())
        else:
            for brick in bricks:
                self.brick_shapes_queue.append(brick)
        self.select_next_brick()

    def resize_height(self, *args):
        self.height = self.width / TETRIS_BOARD_COLS * TETRIS_BOARD_ROWS

    def get_block_widget(self, position) -> Optional[TetrisBlockWidget]:
        if 0 <= position.y < TETRIS_BOARD_ROWS and 0 <= position.x < TETRIS_BOARD_COLS:
            return self.blocks[position.y][position.x]
        else:
            return None

    def get_full_rows(self) -> [(int, [TetrisBlockWidget])]:
        """
        Not used anymore.
        :return: returns a list with the fully completed rows index and the blocks in that row from top too bottom.
        """
        for row_n, row_blocks in enumerate(self.blocks):
            if all(map(lambda block: block.occupied_by is not None, row_blocks)):
                yield row_n, row_blocks

    def get_active_blocks(self):
        """
        Gets the changes from the last time the GameField state was recorded and the current state of the GameField
        Also removes the previous tracking and start new from the current state.
        """
        return list(map(lambda block: (block.position.as_tuple(), list(block.occupied_by.color)), filter(lambda block: block.occupied_by is not None, self.get_blocks_as_1D())))


    def apply_active_blocks(self, active):
        active_positions = set()
        for (block_x, block_y), color in active:
            block = self.get_block_widget(Position(x=block_x, y=block_y))
            single_brick = TetrisBrick(game_field=self, position=block.position, shape=BrickShape.get_single_block_brick_shape(), init_color=color)
            block.occupied_by = single_brick
            active_positions.add(block.position)
        inactive = set(map(lambda block: block.position, self.get_blocks_as_1D())).difference(active_positions)
        for position in inactive:
            block = self.get_block_widget(position)
            block.occupied_by = None

    def get_blocks_as_1D(self):
        return numpy.ravel(numpy.array(self.blocks))

    def get_lowest_full_row(self) -> (int, [TetrisBlockWidget]):
        """
        :return: returns the first full row encountered from the bottom of the field.
        """
        for row_n, row_blocks in enumerate(reversed(self.blocks)):
            if all(map(lambda block: block.occupied_by is not None, row_blocks)):
                return row_n, row_blocks
        return None

    def clear_full_rows(self):
        """
        Clears the first full row from bottom to top and shifts the rows above down until all full rows are cleared.
        """
        combo = 0
        while full_rows := list(self.get_full_rows()):
            first_full_row_index, first_full_row_blocks = full_rows[-1]
            for block in first_full_row_blocks:
                block.occupied_by = None
            self.shift_rows_down(from_row_index=first_full_row_index-1)
            combo += 1
        if combo > 0:
            self.score += combo**combo

    def shift_rows_down(self, from_row_index):
        """
        Recursively shifts all rows above from_row_index down 1 blocks.
        """
        for to_shift_block in self.blocks[from_row_index]:
            destination_row = self.blocks[from_row_index+1]
            if to_shift_block.occupied_by is not None:
                destination_block: TetrisBlockWidget = destination_row[to_shift_block.position.x]
                if destination_block.occupied_by is None:
                    destination_block.occupied_by = to_shift_block.occupied_by
                else:
                    raise Exception('Shifting to occupied block. This is a bug.')
                to_shift_block.occupied_by = None
        if from_row_index >= 1:
            self.shift_rows_down(from_row_index-1)

    def create_brick_shape(self) -> BrickShape:
        # return BrickShape.get_shape(-3)
        return BrickShape.random_shape()

    def select_next_brick(self):
        self.current_brick = TetrisBrick(game_field=self, position=Position(int(TETRIS_BOARD_COLS/2), 0), shape=self.brick_shapes_queue.popleft())
        self.brick_shapes_queue.append(self.create_brick_shape())

    def move_current_brick(self, direction: Direction):
        self.current_brick.move(direction)

    def rotate_current_brick(self):
        self.current_brick.rotate()

    def map_brick_shape_to_blocks(self, brick_shape: BrickShape, position: Position) -> [TetrisBlockWidget]:
        for template_block in brick_shape.current_rotation_shape():
            pos = Position(position.x + template_block[0], position.y + template_block[1])
            yield self.get_block_widget(position=pos)

    def __str__(self):
        return f'gameField: {self.__repr__()} of {self.player})'



class Menu(BoxLayout, RootAccess):
    join_lobby_popup = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(Menu, self).__init__(**kwargs)

    def play_singleplayer(self):
        self.app_root.add_player(self.app_root.player)
        self.app_root.start_game()

    def play_multiplayer(self):
        self.join_lobby_popup = LobbyPopup()
        self.join_lobby_popup.open()


class TetrisRoot(BoxLayout, ConnectionListener):
    players_field_dict: {Position: GameField} = {}
    player: Player = ObjectProperty(None)
    multiplayer_server_available: bool = BooleanProperty(False)
    main_menu: Menu = ObjectProperty(None)
    lobbies: {int, GameLobby} = DictProperty({})
    current_lobby: GameLobby = ObjectProperty(None)
    # join_lobby_popup: LobbyPopup = ObjectProperty(None)

    def __init__(self, hostname, port, **kwargs):
        super(TetrisRoot, self).__init__(**kwargs)
        self._keyboard = Window.request_keyboard(None, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        self.spacing = 10

        self.player = Player("You", local=True)
        self.main_menu = self.ids.main_menu
        self.in_menu = True

        self.hostname = hostname
        self.port = port
        self.Connect((hostname, port))
        Clock.schedule_interval(self.update_connection, 0.001)

    def start_gameloop(self, *_):
        Clock.schedule_interval(self.game_loop, 0.5)

    def game_loop(self, dt):
        for player, game_field in self.players_field_dict.items():
            if player == self.player and not game_field.game_over and game_field.current_brick is not None:
                game_field.move_current_brick(direction=Direction.DOWN)
                self.send_data_to_other_players()

    def add_player(self, player):
        new_player_field = GameField(player=player)
        self.players_field_dict[player] = new_player_field

    def start_game(self):
        self.remove_widget(self.main_menu)
        for player, field in self.players_field_dict.items():
            self.add_widget(field)
        Window.size = (600*len(self.players_field_dict), Window.size[1])
        self.in_menu = False
        self.start_gameloop()

    def game_over(self):
        field = self.players_field_dict[self.player]
        field.game_over = True
        if self.player.firebase_account_id is not None:
            FIREBASE_CONNECTION.set_highscore(self.player.firebase_account_id, field.score)

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] in ['right', 'left', 'down'] and not self.in_menu:
            game_field = self.players_field_dict[self.player]
            if not game_field.game_over:
                game_field.move_current_brick(direction=Direction[keycode[1].upper()])
                #self.send_changes_to_other_players()
        elif keycode[1] == 'r' and not self.in_menu:
            game_field = self.players_field_dict[self.player]
            if not game_field.game_over:
                game_field.rotate_current_brick()
               # self.send_changes_to_other_players()
        elif keycode[1] == 'enter' and not self.in_menu:
            print('ENTER')
        return True

    def update_connection(self, dt):
        self.Pump()
        connection.Pump()

    def send_data_to_other_players(self):
        # player_field: GameField = self.players_field_dict[self.player]
        # activated, deactivated = player_field.get_changes()
        player_field: GameField = self.players_field_dict[self.player]
        active = player_field.get_active_blocks()
        if self.current_lobby:
            player_field: GameField = self.players_field_dict[self.player]
            active = player_field.get_active_blocks()
            connection.Send({"action": "send_data_to_other_players",
                             "lobby_id": self.current_lobby.lobby_id,
                             "player_id": self.player.multiplayer_network_id,
                             "active": active,
                             "score": player_field.score
                             })


    def Network_receive_data_from_other_players(self, data):
        other_player_id = data['player_id']
        player = self.current_lobby.players[other_player_id]
        if player is not self.player:
            other_player_field: GameField = self.players_field_dict[player]
            other_player_field.apply_active_blocks(active=data['active'])
            other_player_field.score = data['score']


    def Network_PlayerInit(self, data):
        print("Connected with server.")
        self.multiplayer_server_available = True
        self.main_menu.ids.play_multiplayer_btn.disabled = False
        self.player.multiplayer_network_id = data['multiplayer_network_id']
        connection.Send({"action": "lobby_list"})


    def Network_join_lobby(self, data):
        """ Confirmation from the server that you have joined the lobby. """
        lobby_data = data['lobby_data']
        self.current_lobby = self.lobbies[lobby_data['lobby_id']]
        self.main_menu.join_lobby_popup.load_lobby_players()

    def Network_lobby_list(self, data):
        self.lobbies = {}
        for lobby_data in data['lobbies']:
            self.lobbies[lobby_data['lobby_id']] = GameLobby(lobby_id=lobby_data['lobby_id'],
                                                             lobby_name=lobby_data['lobby_name'],
                                                             players=[])
            self.lobbies[lobby_data['lobby_id']].update(lobby_data)
        if self.main_menu.join_lobby_popup is not None:
            self.main_menu.join_lobby_popup.refresh()

    def Network_update_lobbies(self, data):
        received_lobbies = data['lobbies']
        for received_lobby_data in received_lobbies:
            if received_lobby_data['lobby_id'] in self.lobbies:
                local_lobby_object = self.lobbies[received_lobby_data['lobby_id']]
                local_lobby_object.update(received_lobby_data)
            else:
                print("Error: Received a lobby that does not exist locally. ", received_lobby_data)

            if self.main_menu.join_lobby_popup is not None:
                child: LobbyRow
                self.main_menu.join_lobby_popup.load_lobby_players()
                for child in self.main_menu.join_lobby_popup.scroll_grid.children:
                    if child.game_lobby.lobby_id == received_lobby_data['lobby_id']:
                        child.update()

            # if self.current_loby != None and self.current_loby.loby_data['multiplayer_network_id'] == loby['multiplayer_network_id']:
            #     self.current_loby.update(loby_data=loby)

    def Network_match_started(self, data):
        self.main_menu.join_lobby_popup.dismiss()
        self.add_player(player=self.player)
        lobby = self.lobbies[data['lobby_id']]
        for player_network_id, player in lobby.players.items():
            if player != self.player:
                self.add_player(player)
        self.start_game()


    def Network_disconnected(self, data):
        if self.multiplayer_server_available:
            print("disconnected from the server")
            connection.Close()
            exit()


class TetrisGameClient(App):
    def build(self):
        CoreWindow.size = (WIN_WIDTH, WIN_HEIGHT)
        return TetrisRoot("localhost", 1433)

    def on_stop(self):
        ...


if __name__ == '__main__':
    TetrisGameClient().run()
