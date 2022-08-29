import firebase_admin
import requests
from firebase_admin import credentials, db
from firebase_admin import auth
from firebase_admin.auth import UserRecord
import json

CRED = credentials.Certificate("tetrispyauth-firebase-adminsdk.json")
WEB_API_KEY = 'AIzaSyBCjeVjHZXEbT01K4f5TVNnzIh_IlFu5dk'
DB_URL = "https://tetrispyauth-default-rtdb.europe-west1.firebasedatabase.app/"

class FirebaseConnection:
    def __init__(self):
        self.app = firebase_admin.initialize_app(CRED, {
            'databaseURL': DB_URL
        })
        self.db_ref = db.reference("/")

    def register_user(self, email, password, display_name):
        payload = json.dumps({
            "email": email,
            "password": password,
            "displayName": display_name,
            "returnSecureToken": True
        })
        r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signUp",
                          params={"key": WEB_API_KEY},
                          data=payload).json()
        if not "error" in r:
            user_id = r['localId']
            FIREBASE_CONNECTION.db_ref.update({user_id: 0})
            #self.db_ref.set({r[]})
        return r

    def login_user(self, email, password):
        payload = json.dumps({
            "email": email,
            "password": password,
            "returnSecureToken": True
        })

        r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
                          params={"key": WEB_API_KEY},
                          data=payload).json()
        return r

    def get_user_data(self, id_token):
        payload = {
            'idToken': id_token
        }
        r = requests.post('https://identitytoolkit.googleapis.com/v1/accounts:lookup',
                          params={"key": WEB_API_KEY},
                          data=payload)
        if 'error' in r.json().keys():
            return {'status': 'error', 'message': r.json()['error']['message']}
        if 'users' in r.json():
            return {'status': 'success', 'data': r.json()['users']}

    def set_highscore(self, player_ud, score):
        self.db_ref.child(player_ud).update({"score": score})

FIREBASE_CONNECTION = FirebaseConnection()


if __name__ == '__main__':
    ...
    # user = None
    #response = FIREBASE_CONNECTION.register_user("arthurvanremoortel@hotmail.com", "arthur", "Arthur2")
    # if "error" in response:
    #     if response['error']['message'] == 'EMAIL_EXISTS':
    #         user = fb.login_user("arthurvanremoortel@hotmail.com", "arthur")
    # else:
    #     user = response
    #FIREBASE_CONNECTION.db_ref.set({"test": "hello"})


