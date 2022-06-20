

class Client_node:

    def __init__(self, roomid, login, password, apikey, ws, clientid, roomname, organization):
        self.roomid = roomid
        self.login = login
        self.password = password
        self.apikey = apikey
        self.ws = ws

        self.clientid = clientid
        self.roomname = roomname
        self.organization = organization