import websockets
import asyncio
import json
from anchor import Anchor


"""Класс ноды"""
class Node:

    def __init__(self, login, password, roomid, server_ip, server_port):
        self.server_ip = server_ip       # ip-адрес сервера
        self.server_port = server_port   # порт сервера
        self.login = login               # логин ноды
        self.password = password         # пароль ноды
        self.apikey = ""                 # apikey - ключ безопасности для общения с сервером
        self.buffer = []                 # массив с сообщениями от маяков
        self.enabled_anchors = []        # массив с активными маяками
        self.disabled_anchors = []       # массив с неактивными маяками
        self.anchors_tasks = []          # массив с задачами для маяков (задачи из массива выполняются асинхронно)
        self.config = None               # config для маяков (приходит с сервера)
        self.rf_config = None            # rf_config для маяков (приходит с сервера)
        self.config_flag = False         # флаг проверки наличия config
        self.rf_config_flag = False      # флаг проверки наличия rg_config
        self.start_flag = False          # флаг проверки рабочего состояния ноды
        self.stop_flag = True            # флаг проверки нерабочего состояния ноды
        self.clientid = ""               # ID клиента
        self.roomid = roomid             # ID комнаты, где установлена нода
        self.roomname = ""               # Название комнаты
        self.organization = ""           # Название организации

        self.testmsg = {'type': 'CS_RX', 'sender': b'\xb6\xd1\xd0M\x05 \xa3\r', 'receiver': b'\x04\xd2\xd0M\x05 \xa3\r', 'seq': 3, 'timestamp': 0.6012962916917067}

    """Функция обработки ноды"""
    async def node_handler(self):
        url = f"ws://{self.server_ip}:{self.server_port}" # url-адрес сервера
        async with websockets.connect(url, ping_interval=None) as ws: # открытие подключения к серверу
            print("NODE CONNECTED TO SERVER: " + str(self.server_ip) + ":" + str(self.server_port))
            await ws.send(json.dumps({"action": "Login", "login": self.login, "password": self.password, "roomid": self.roomid})) # отправка сообщения авторизации на сервер
            await asyncio.gather(self.node_produce(ws), self.node_receive(ws)) # запуск асинхронной работы приемной и передающей функций ноды

    """Функция передачи ноды"""
    async def node_produce(self, ws):
        while True: # запуск бесконечного цикла для непрерывной работы функции
            if self.buffer: # если массив сообщений не пустой -> отправляет сообщения на сервер
                message = self.buffer.pop(0) # взятие первого сообщения и его удаление из массива
                message["sender"] = str(hex(message["sender"][1])[2:]) + str(hex(message["sender"][0])[2:]) # для корректной отправки данных в формате JSON заменяем байтовое поле с названием маяка на его сокращенное название типа str
                message["receiver"] = str(hex(message["receiver"][1])[2:]) + str(hex(message["receiver"][0])[2:])# для корректной отправки данных в формате JSON заменяем байтовое поле с названием маяка на его сокращенное название типа str
                log_message = {"action": "Log", "apikey": self.apikey, "organization": self.organization ,"name": self.roomname, "info": "log message", "roomid": self.roomid, "status": "true", "data": message} # сообщение типа Log для оптравки на сервер
                await ws.send(json.dumps(log_message)) # отправка сообщения на сервер
            await asyncio.sleep(0.01) # чтобы у других функций было время для работы в асинхронном режиме, функция передачи засыпает на определенное время в цикле и передает право на работу другим функциям

    """Функция приема ноды"""
    async def node_receive(self, ws):
        while True: # запуск бесконечного цикла для непрерывной работы функции
            message = json.loads(await ws.recv()) # прием сообщения от сервера
            print("MESSAGE FROM SERVER " + str(message))

            if message["status"] == "false": # если статус false - пачать предупреждающего сообдения
                print("---WARNING--- " + str(message["data"]) + " ---WARNING---")

            elif message["action"] == "Login" and message["status"] == "true": # обработка авторизации
                await self.login_on_the_server(message)

            elif message["action"] == "SetConfig" and message["status"] == "true": # обаботка установки config
                await self.set_config(message)

            elif message["action"] == "SetRfConfig" and message["status"] == "true": # обаботка установки rf_config
                await self.set_rf_config(message)

            elif message["action"] == "Start" and message["status"] == "true": # обработка команды start
                await self.start(ws)

            elif message["action"] == "Stop" and message["status"] == "true": # обработка команды stop
                await self.stop()

    """Функция аторизации на сервере"""
    async  def login_on_the_server(self, message):
        self.clientid = message["data"]["clientid"] # ID клиента
        self.roomname = message["data"]["roomname"] # Название комнаты
        self.organization = message["data"]["name"] # Название организации
        self.apikey = message["data"]["apikey"]     # apikey - ключ безопасности для общения с сервером
        print("APIKEY: " + self.apikey)

    async def set_config(self, message):
        self.config = message["data"] # config для маяков (приходит с сервера)
        if self.start_flag: await self.stop() # если нода уже работает, а новый конфиг пришел -> останавливаем работу ноды

        """Так как соединение маяков и ноды происходит по socket-соединению, то разрывать его нельзя, поэтому необходимо написать обработчик конфигурации и переконфигарация старых(неактивных) и новых(активных) маяков"""

        """Цикл для проверки: есть ли уже в акивных на ноде маяках тех, которых нет в новом config, если нет -> переводим маяк в неактвное состояние, если есть такой же маяк и в новом config, и в уже активных -> переконфигурция маяка"""
        for anchor in reversed(self.enabled_anchors): # reversed - для того чтобы при удалении старого маяка из массива не нарушался его перебор в цикле
            disable_anchor_flag = True # флаг проверки неактивного маяка
            for config in reversed(self.config): # reversed - для того чтобы при удалении старого маяка из массива не нарушался его перебор в цикле
                if anchor.IP == config["ip"]: # сравнение двух ip-адресов
                    disable_anchor_flag = False # отключение флага если тот же маяк есть
                    await anchor.reconfig(config)  # переконфигурация
            if disable_anchor_flag: # если флаг остался -> перевод маяка в неактивный режим
                self.disabled_anchors.append(anchor) # добавление маяка в массив неактивных маяков
                self.enabled_anchors.remove(anchor) # удаление маяка из массива активных маяков
                print("OLD ANCHOR " + str(anchor.IP) + " DISABLED")

        """Цикл для добавления новых маяков из config"""
        for config in reversed(self.config): # reversed - для того чтобы при удалении старого маяка з массива не нарушался его перебор в цикле
            new_anchor_flag = True # флаг для проверки наличия нового маяка
            for anchor in reversed(self.enabled_anchors):  # reversed - для того чтобы при удалении старого маяка з массива не нарушался его перебор в цикле
                if anchor.IP == config["ip"]: # сравнение двух ip-адресов
                    new_anchor_flag = False # отключение флага если такой же маяк есть
            if new_anchor_flag: # если флаг остался -> в config и в массиве активных маяков нет похожего
                if self.disabled_anchors: # проверка есть ли неактивные маяки, если есть -> ищем новый маяк в массиве неактивных маяков
                    disable_anchor_flag = True # флаг для проверки наличия нового маяка в массиве неактивных маяков
                    """Цикл для проверки есть ли новых маяк из config в неактвных маяках - если есть добавление его в общий массив и переконфигурация"""
                    for anchor in reversed(self.disabled_anchors): # reversed - для того чтобы при удалении старого маяка из массива не нарушался его перебор в цикле
                        if anchor.IP == config["ip"]: # сравнение двух ip-адресов
                            disable_anchor_flag = False # отключение флага если такой же маяк есть
                            await anchor.reconfig(config) # переконфигурация
                            self.enabled_anchors.append(anchor) # добавление маяка в массив активных маяков
                            self.disabled_anchors.remove(anchor) # удаление маяка из массива неативных маяков
                    if disable_anchor_flag: # если флаг не отключился -> маяк новый
                        anchor = Anchor(config) # экземпляр класса маяка
                        self.enabled_anchors.append(anchor)  # добавление маяка в массив активных маяков
                else: # если массив с неактивными маяками пустой -> маяк точно новый
                    anchor = Anchor(config) # экземпляр класса маяка
                    self.enabled_anchors.append(anchor) # добавление маяка в массив активных маяков

        if self.rf_config_flag: # если с сервера уже приходил rf_config -> устанавливаем его
            for anchor in self.enabled_anchors:
                await anchor.set_rf_config(self.rf_config) # установка rf_config
                print(anchor.IP + " SET RF_CONFIG")

        self.config_flag = True # активация флага наличия config
        print("NODE HAVE " + str(len(self.enabled_anchors)) + " ACTIVE ANCHORS")

    async def set_rf_config(self, message):
        if self.start_flag: await self.stop()
        self.rf_config = message["data"][0] # rf_config для маяков (приходит с сервера), [0], т.к. rf_config лежит в 0 элементе массива [{rf_config}]
        if self.config_flag: # установка rf_config возможна только если уже есть config, поэтому проверяем это уловие
            for anchor in self.enabled_anchors:
                await anchor.set_rf_config(self.rf_config) # установка rf_config
                print(anchor.IP + " SET RF_CONFIG")
        self.rf_config_flag = True # активация флага наличия rf_config

    async def start(self, ws):
        if self.config_flag and self.rf_config_flag: # старт возможен только если уже пришли config и rf_config, поэтому проверяем это условие
            print("NODE START")
            for anchor in self.enabled_anchors: # пробежка по элементам общего массива маяков
                await anchor.start_spam() # запуск спама сообщений от маяков
            for anchor in self.enabled_anchors: # пробежка по элементам общего массива маяков
                self.anchors_tasks.append(asyncio.create_task(
                    anchor.anchor_handler(self.buffer))) # добавление функции обработки маяка в массив задач маяков и асинхронный запуск этих функций
        if not self.config_flag: # проверка наличия config
            await ws.send(json.dumps({"action": "start", "status": "false", "apikey": self.apikey, "data": "NEED CONFIG"}))  # отправка сообщения на сервер о необходимости config, если его нет
        if not self.rf_config_flag: # проверка наличия rf_config
            await ws.send(json.dumps({"action": "start", "status": "false", "apikey": self.apikey, "data": "NEED RF_CONFIG"}))  # отправка сообщения на сервер о необходимости rf_config, если его нет

        if self.config_flag and self.rf_config_flag:
            self.start_flag = True # включене флага проверки рабочего состояния ноды
            self.stop_flag = False # выключене флага проверки нерабочего состояния ноды

    async def stop(self):
        for anchor in self.enabled_anchors:
            await anchor.stop() # остановка спама сообщений от маяков
        for task in reversed(self.anchors_tasks): # reversed - для того чтобы при удалении старой задачи из массива не нарушался его перебор в цикле
            task.cancel() # отмена асинхронных задачи маяка
            self.anchors_tasks.remove(task) # удаление задачи из массива асинхронных задач для маяков
        print("NODE STOP")
        self.start_flag = False # выключене флага проверки рабочего состояния ноды
        self.stop_flag = True # включене флага проверки нерабочего состояния ноды

"""Главная функция включения ноды"""
if __name__ == '__main__':
    node_login = "TestOrg"          # логин ноды
    node_password = "TestOrgPass"   # пароль ноды
    node_roomid = "1"               # ID комнаты, где установлена нода
    node_server_ip = "127.0.0.1"    # ip-адрес сервера
    # node_server_ip = "10.3.168.123"
    node_server_port = "9000"       # порт сервера
    node = Node(node_login, node_password, node_roomid, node_server_ip, node_server_port) # экземпляр класса ноды
    loop = asyncio.get_event_loop() # асинхронная петля
    loop.run_until_complete(node.node_handler()) # запуск асинхронной петли -> функции обработки ноды