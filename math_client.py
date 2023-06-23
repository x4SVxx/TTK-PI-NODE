class Client_math:

    def __init__(self, roomid, login, password, ws):
        self.roomid = roomid               # ID комнаты, где установлена нода
        self.login = login                 # логин
        self.password = password           # пароль
        self.ws = ws