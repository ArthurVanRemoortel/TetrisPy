from PodSixNet.Channel import Channel
from PodSixNet.Server import Server
from time import sleep
from weakref import WeakKeyDictionary


class PlayerChannel(Channel):
    def __init__(self, *args, **kwargs):
        Channel.__init__(self, *args, **kwargs)
        self.displayName = "anonymous"
        self.multiplayer_network_id = str(self._server.NextId())
        self.firebase_account_id = None

    def Close(self):
        self._server.Disconnected(self)

    def Network_lobby_list(self, data):
        self.Send({"action": "lobby_list", "lobbies": [lobby for lobby in self._server.lobbies.values()]})

    def Network_player_firebase_login(self, data):
        self.firebase_account_id = data['firebase_id']
        self.displayName = data['displayName']

    def Network_player_joins_lobby(self, data):
        lobby_id = data['lobby_id']
        if (self.multiplayer_network_id, self.firebase_account_id, self.displayName) not in self._server.lobbies[lobby_id]['players']:
            self._server.lobbies[lobby_id]['players'].append((self.multiplayer_network_id, self.firebase_account_id, self.displayName))
            self._server.SendlobbiesToAll(lobbies=[self._server.lobbies[lobby_id]])
            self.Send({"action": "join_lobby", "lobby_data": self._server.lobbies[lobby_id]})

    def Network_player_leaves_lobby(self, data):
        self._server.PlayerLeftlobby(player=self, lobby=self._server.lobbies[data['lobby_id']])

    def Network_player_started_match(self, data):
        lobby_id = data['lobby_id']
        self._server.StartMatch(lobby=self._server.lobbies[lobby_id])

    def Network_player_data(self, data):
        self._server.SendPlayerData(player=self, lobby_data=data['lobby_data'], data=data['data'])

    def Network_send_data_to_other_players(self, data):
        self._server.send_data_to_other_players(data)


class MultiTetrisServer(Server):
    channelClass = PlayerChannel

    def __init__(self, *args, **kwargs):
        Server.__init__(self, *args, **kwargs)
        self.last_id = 0
        self.players = WeakKeyDictionary()
        self.lobbies = {}
        for i in range(10):
            lobby_id = self.NextId()
            lobby_data = {'lobby_name': "Public lobby {}".format(i+1), 'admin': None, 'players': [],
                          'lobby_id': lobby_id, 'public': True
                          }
            self.lobbies[lobby_id] = lobby_data
        print('Server launched')

    def NextId(self):
        self.last_id += 1
        return self.last_id

    def Connected(self, player, addr):
        print("New Player" + str(player.addr) + player.multiplayer_network_id + player.displayName)
        self.players[player] = True
        player.Send({"action": "PlayerInit", "multiplayer_network_id": player.multiplayer_network_id})

    def send_data_to_other_players(self, data):
        received_player_id = data['player_id']
        received_lobby_id = data['lobby_id']
        for other_player_tuple in self.lobbies[received_lobby_id]['players']:
            other_player_network_id = other_player_tuple[0]
            other_player_channel: PlayerChannel = self.get_player(other_player_network_id)
            if other_player_channel is not None:
                if other_player_channel.multiplayer_network_id != received_player_id:
                    other_player_channel.Send({"action": "receive_data_from_other_players",
                                               "player_id": received_player_id,
                                               "active": data['active'],
                                               "score": data['score']
                                               })

    def Disconnected(self, player):
        for lobby_id, lobby_data in self.lobbies.items():
            if (player.multiplayer_network_id, player.firebase_account_id, player.displayName) in lobby_data['players']:
                self.PlayerLeftlobby(player=player, lobby=lobby_data)
        del self.players[player]

    def PlayerLeftlobby(self, player, lobby):
        lobby['players'].remove((player.multiplayer_network_id, player.firebase_account_id, player.displayName))
        if lobby['admin'] is not None and player.multiplayer_network_id == lobby['admin'][0]:
            if len(lobby['players']) == 0 and lobby['public']:
                lobby['admin'] = None
            elif len(lobby['players']) == 0 and not lobby['public']:
                del self.lobbies[lobby['multiplayer_network_id']]
            elif len(lobby['players']) != 0 and lobby['public']:
                lobby['admin'] = lobby['players'][0]

        self.SendlobbiesToAll(lobbies=[lobby])

    def StartMatch(self, lobby):
        for player_tuple in lobby['players']:
            player = self.get_player(player_network_id=player_tuple[0])
            player.Send({"action": "match_started", "lobby_id": lobby['lobby_id']})


    def SendToAll(self, data):
        [p.Send(data) for p in self.players]

    def SendlobbiesToAll(self, lobbies):
        self.SendToAll({"action": "update_lobbies", "lobbies": [lobby for lobby in lobbies]})

    def get_player(self, player_network_id):
        for player in self.players:
            if player.multiplayer_network_id == player_network_id:
                return player
        return None


    def Launch(self):
        while True:
            self.Pump()
            sleep(0.001)

myserver = MultiTetrisServer(localaddr=("localhost", 1433))
myserver.Launch()
