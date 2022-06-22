class Client_node:

    def __init__(self, roomid, login, password, clientid, roomname, organization, apikey, ws):
        self.roomid = roomid
        self.clientid = clientid
        self.roomname = roomname
        self.organization = organization
        self.login = login
        self.password = password
        self.apikey = apikey
        self.ws = ws