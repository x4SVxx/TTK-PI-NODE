class Client_node:

    def __init__(self, roomid, login, password, clientid, roomname, organization, apikey, ws):
        self.roomid = roomid               # ID комнаты, где установлена нода
        self.clientid = clientid           # ID клиента, к которому приязана нода
        self.roomname = roomname           # название комнаты
        self.organization = organization   # название организации
        self.login = login                 # логин
        self.password = password           # пароль
        self.apikey = apikey               # ключ-безопасности
        self.ws = ws                       # экземпляр websocket-соединения