class Client_client:

    def __init__(self, login, password, clientid, organization, apikey, ws):
        self.login = login                 # логин
        self.password = password           # пароль
        self.clientid = clientid           # ID клиента
        self.organization = organization   # название организации
        self.apikey = apikey               # ключ-безопасности
        self.ws = ws                       # экземпляр websocket-соединения