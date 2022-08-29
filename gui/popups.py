from PodSixNet.Connection import connection
from kivy.properties import StringProperty, ObjectProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from firebase_connection import FIREBASE_CONNECTION
from helpers import RootAccess, GameLobby


class ThemedPopup(Popup):
    pass


class FirebaseLoginPopup(ThemedPopup, RootAccess):
    mode = StringProperty("")

    def __init__(self, mode, join_lobby_popup, **kwargs):
        super(FirebaseLoginPopup, self).__init__(**kwargs)
        self.mode = mode
        self.join_lobby_popup = join_lobby_popup
        self.root_box = self.ids.root_box
        self.email_input = TextInput(size_hint_y=None, height='50dp', hint_text="email")
        #self.email_input.text = "arthurvanremoortel@test.com"
        self.password_input = TextInput(size_hint_y=None, height='50dp', hint_text="password", password=True)
        #self.password_input.text = "arthur"
        self.username_input = TextInput(size_hint_y=None, height='50dp', hint_text="username")
       # self.username_input.text = "Arthur1"
        self.error_label = Label(size_hint_y=None, height='50dp')

        if mode == "login":
            self.set_gui_login()
        elif mode == "register":
            self.set_gui_register()
        self.root_box.add_widget(Button(text="Cancel", on_press=self.dismiss, size_hint_y=None, height='50dp'))
        self.root_box.add_widget(Button(text="Confirm", on_press=self.confirm, size_hint_y=None, height='50dp'))
        self.root_box.add_widget(self.error_label)
        self.root_box.add_widget(Widget())

    def set_gui_login(self):
        self.root_box.add_widget(self.email_input)
        self.root_box.add_widget(self.password_input)

    def set_gui_register(self):
        self.root_box.add_widget(self.email_input)
        self.root_box.add_widget(self.password_input)
        self.root_box.add_widget(self.username_input)


    def cancel(self):
        ...

    def confirm(self, *_):
        if self.mode == "login":
            response = self.app_root.player.login(FIREBASE_CONNECTION,
                                                  self.email_input.text,
                                                  self.password_input.text)
            if "error" in response:
                self.error_label.text = response['error']["message"]
            else:
                connection.Send({"action": "player_firebase_login",
                                 "firebase_id": self.app_root.player.firebase_account_id,
                                 "displayName": self.app_root.player.firebase_info['displayName']
                                 })
                self.dismiss()

        elif self.mode == "register":
            response = self.app_root.player.register(FIREBASE_CONNECTION,
                                                     self.email_input.text,
                                                     self.password_input.text,
                                                     self.username_input.text)
            if "error" in response:
                self.error_label.text = response['error']["message"]
            else:
                connection.Send({"action": "player_firebase_login",
                                 "firebase_id": self.app_root.player.firebase_account_id,
                                 "displayName": self.app_root.player.firebase_info['displayName']
                                 })
                self.dismiss()

    def on_dismiss(self):
        self.join_lobby_popup.refresh()


class LobbyPopup(ThemedPopup, RootAccess):
    leave_lobby_btn: Button = ObjectProperty()
    start_game_btn: Button = ObjectProperty()
    players_scroll_grid: GridLayout = ObjectProperty()
    current_lobby_label: Label = ObjectProperty()
    selected_lobby: GameLobby = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(LobbyPopup, self).__init__(**kwargs)
        self.scroll_grid = self.ids.scroll_grid
        self.login_bar = self.ids.login_bar
        self.players_scroll_grid = self.ids.players_scroll_grid

    def open_login_popup(self):
        FirebaseLoginPopup(mode="login", join_lobby_popup=self).open()

    def open_register_popup(self):
        FirebaseLoginPopup(mode="register", join_lobby_popup=self).open()

    def refresh(self):
        if self.app_root.player.logged_in:
            self.title += "    -    Logged in as: " + self.app_root.player.name
            self.login_bar.clear_widgets()
            self.login_bar.height = 0
            self.scroll_grid.clear_widgets()
            for lobby_in, lobby in self.app_root.lobbies.items():
                self.scroll_grid.add_widget(LobbyRow(game_lobby=lobby, lobby_popup=self))

    def on_join(self, lobby: GameLobby):
        if lobby != self.selected_lobby and self.selected_lobby is not None:
            connection.Send({"action": "player_leaves_lobby", "lobby_id": self.selected_lobby.lobby_id})
        self.selected_lobby = lobby
        connection.Send({"action": "player_joins_lobby", "lobby_id": self.selected_lobby.lobby_id})

    def load_lobby_players(self):
        if self.selected_lobby:
            self.players_scroll_grid.clear_widgets()
            for player in self.selected_lobby.players.values():
                self.players_scroll_grid.add_widget(Label(text=player.name, size_hint_y=None, height='30dp'))

    def start_game(self):
        if self.selected_lobby is not None:
            connection.Send({"action": "player_started_match", "lobby_id": self.selected_lobby.lobby_id})


class LobbyRow(BoxLayout, RootAccess):
    lobby_popup: LobbyPopup = ObjectProperty()
    game_lobby: GameLobby = ObjectProperty(None)
    number_of_players = NumericProperty(0)

    def __init__(self, **kwargs):
        super(LobbyRow, self).__init__(**kwargs)
        self.number_of_players = len(self.game_lobby.players)

    def on_join(self):
        self.lobby_popup.on_join(self.game_lobby)

    def update(self):
        self.number_of_players = len(self.game_lobby.players)


