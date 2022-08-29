from kivy.app import App
from typing import Generic, TypeVar, Union
from enum import Enum

T = TypeVar("T")


class RootAccess(Generic[T]):
    """
    Provides an easy way to access the root widget off the application instead of self.parent.parent...
    """
    _app_root_reference: T = None

    @property
    def app_root(self) -> T:
        if self._app_root_reference is None:
            self._app_root_reference = App.get_running_app().root
        return self._app_root_reference


class Direction(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

    def to_position_offset(self) -> (int, int):
        if self is Direction.DOWN:
            return 0, 1
        elif self is Direction.UP:
            return 0, -1
        elif self is Direction.LEFT:
            return -1, 0
        else:  # RIGHT
            return 1, 0


class Position(object):
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def add_offset(self, offset: (int, int)) -> 'Position':
        self.x += offset[0]
        self.y += offset[1]
        return self  # TODO: Is this good practice?

    def next(self, direction: Direction, amount: int = 1) -> 'Position':
        return Position(self.x, self.y).add_offset(direction.to_position_offset())

    def as_tuple(self) -> (int, int):
        return self.x, self.y

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self):
        return hash((self.x, self.y))

    def __eq__(self, other) -> bool:
        if type(other) is not Position:
            return False
        return (self.x, self.y) == (other.x, other.y)

    def __ne__(self, other) -> bool:
        return not(self == other)


class Player(object):
    def __init__(self, name, local=True):
        self.name = name
        self.local = local
        self.multiplayer_network_id = None
        self.logged_in = False
        self.firebase_info = None
        self.firebase_account_id = None

    def login(self, firebase_connection, email, password):
        response = firebase_connection.login_user(email, password)
        if "error" not in response:
            self.firebase_info = response
            self.firebase_account_id = response['localId']
            self.logged_in = True
            self.update_info()
        return response

    def register(self, firebase_connection, email, password, display_name):
        response = firebase_connection.register_user(email, password, display_name)
        if "error" not in response:
            self.firebase_info = response
            self.firebase_account_id = response['localId']
            self.logged_in = True
            self.update_info()
        return response

    def update_info(self):
        self.name = self.firebase_info['displayName']

    def __str__(self):
        return f"Player: {self.name}, local={self.local}, network_id={self.multiplayer_network_id}"

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash((self.name, self.multiplayer_network_id))

    def __eq__(self, other):
        if type(other) is not Player:
            return False
        return (self.name, self.multiplayer_network_id) == (other.name, other.multiplayer_network_id)

    def __ne__(self, other):
        return not(self == other)


class GameLobby(object):
    def __init__(self, lobby_id: int, lobby_name: str, players: [Player]):
        self.lobby_id: int = lobby_id
        self.lobby_name: str = lobby_name
        self.players: {int: Player} = dict((p.multiplayer_network_id, p) for p in players)
        self.admin = None

    def add_player(self, player: Player):
        if player.multiplayer_network_id not in self.players:
            print(f"Added player to {self.lobby_name}: {player}")
            self.players[player.multiplayer_network_id] = player
        if self.admin is None:
            self.admin = self

    def remove_player(self, player: Player):
        if player.multiplayer_network_id in self.players:
            print(f"Removed player from {self.lobby_name}: {player}")
            del self.players[player.multiplayer_network_id]
        if self.admin == self.players:
            self.admin = None

    def is_player_in_lobby(self, player: Player):
        return player.multiplayer_network_id in self.players

    def update(self, player_data):
        received_players = player_data['players']
        received_network_ids = []
        for multiplayer_network_id, firebase_account_id, player_name in received_players:
            if multiplayer_network_id not in self.players:
                new_player = Player(name=player_name, local=False)
                new_player.multiplayer_network_id = multiplayer_network_id
                new_player.firebase_account_id = firebase_account_id
                self.add_player(new_player)
            received_network_ids.append(multiplayer_network_id)

        to_remove = []
        for player in self.players.values():
            if player.multiplayer_network_id not in received_network_ids:
                to_remove.append(player)
        for to_remove_player in to_remove:
            self.remove_player(to_remove_player)






