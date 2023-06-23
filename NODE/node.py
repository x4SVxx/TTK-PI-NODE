import websockets
import asyncio
import json
import time
import reports_and_messages as rm
from anchor import Anchor


class Node:
    """Класс ноды"""
    def __init__(self, login, password, roomid, server_ip, server_port):
        self.server_ip = server_ip       # ip-адрес сервера
        self.server_port = server_port   # порт сервера
        self.login = login               # логин ноды
        self.password = password         # пароль ноды
        self.roomid = roomid             # ID комнаты, где установлена нода
        self.apikey = ""                 # apikey - ключ безопасности для общения с сервером
        self.clientid = ""               # ID клиента, к которому привязана нода
        self.roomname = ""               # название комнаты, где установлена нода
        self.name = ""                   # название организации, где установлена нода
        self.log_buffer = []             # массив с сообщениями от маяков
        self.enabled_anchors = []        # массив с активными маяками
        self.disabled_anchors = []       # массив с неактивными маяками
        self.anchors_tasks = []          # массив с задачами для маяков (задачи из массива выполняются асинхронно)
        self.config = None               # config для маяков (приходит с сервера)
        self.rf_config = None            # rf_config для маяков (приходит с сервера)
        self.config_flag = False         # флаг проверки наличия config
        self.rf_config_flag = False      # флаг проверки наличия rg_config
        self.start_flag = False          # флаг проверки рабочего состояния ноды
        self.stop_flag = True            # флаг проверки нерабочего состояния ноды
        self.warning_message = {}        # предупреждающее сообщение на сервер, если на ноде возникла ошибка

    async def NodeHandler(self):
        """Функция обработки ноды"""
        async with websockets.connect(f"ws://{self.server_ip}:{self.server_port}", ping_interval=None) as ws: # открытие соединения с сервером
            print(f"NODE CONNECTED TO SERVER: {self.server_ip}:{self.server_port}")
            await self.MessageToServer(ws, {"action": "Login", "status": "true", "login": self.login, "password": self.password, "roomid": self.roomid})
            await asyncio.gather(self.NodeProduce(ws), self.NodeReceive(ws)) # запуск асинхронной работы приемной и передающей функций ноды

    async def MessageToServer(self, ws, message):
        """Функция отправки сообщения на сервер"""
        await ws.send(json.dumps(message)) # отправка сообщения на сервер
        # print("MESSAGE TO SERVER: " + str(message))

    async def MessageFromServer(self, message):
        """Функция приема сообщений от сервер"""
        print("MESSAGE FROM SERVER " + str(message))

    def MathMessage(self, message):
        """Функция формирования сообщения для математики"""
        math_message = {"action": "SendToMath",
                        "apikey": self.apikey,
                        "orgname": self.name,
                        "organization": self.clientid,
                        "roomid": self.roomid,
                        "name": message["type"],
                        "timestamp": message["timestamp"],
                        "receiver": message["receiver"],
                        "sender": message["sender"],
                        "num1": time.time(),
                        "num2": 123}
        if message["type"] == "CS_RX" or message["type"] == "CS_TX":
            math_message["flag"] = message["seq"]
        if message["type"] == "BLINK":
            math_message["flag"] = message["sn"]
        return math_message

    def LogMessage(self, message):
        """Функция формирующая сообщение для лога"""
        log_message = {"action": "Log",
                       "apikey": self.apikey,
                       "organization": self.clientid,
                       "name": self.name,
                       "info": "log message",
                       "roomid": self.roomid,
                       "status": "true",
                       "data": message}
        return log_message

    async def NodeProduce(self, ws):
        """Функция передачи ноды"""
        while True: # запуск бесконечного цикла для непрерывной работы функции
            if self.log_buffer: # если массив сообщений не пустой -> отправка сообщений на сервер
                # await self.MessageToServer(ws, self.MathMessage(self.log_buffer.pop(0)))
                print(len(self.log_buffer))
            await asyncio.sleep(0.005) # чтобы у других функций было время для работы в асинхронном режиме, функция передачи засыпает на определенное время и передает право на работу другим функциям

    async def NodeReceive(self, ws):
        """Функция приема ноды"""
        while True: # запуск бесконечного цикла для непрерывной работы функции
            message = json.loads(await ws.recv()) # прием сообщения от сервера
            await self.MessageFromServer(message) # обработка сообщения от сервера
            if "action" in message:  # проверка есть ли поле "action" в сообщении
                if "status" in message: # проверка есть ли поле "status" в сообщении
                    if "data" in message: # проверка есть ли поле "data" в сообщении
                        if message["status"] == "true":
                            if message["action"] == "Login": await self.LoginOnTheServer(ws, message) # авторизация
                            elif message["action"] == "SetConfig": await self.SetConfig(ws, message) # установка config
                            elif message["action"] == "SetRfConfig": await self.SetRfConfig(ws, message) # установка rf_config
                            elif message["action"] == "Start": await self.Start(ws) # запуск ноды
                            elif message["action"] == "Stop": await self.Stop(ws) # остановка ноды
                            if message["action"] != "Login" and message["action"] != "SetConfig" and message["action"] != "SetRfConfig" and message["action"] != "Start" and  message["action"] != "Stop": await self.MessageToServer(ws, {"data": "UNKNOWN 'action'"})
                    else: await self.MessageToServer(ws, {"data": "'data' NOT RECEIVED"})
                else: await self.MessageToServer(ws, {"data": "'status' NOT RECEIVED"})
            else:
                if 'status' in message == 'false': pass
                # await self.MessageToServer(ws, {"data": "'action' NOT RECEIVED"})

    async  def LoginOnTheServer(self, ws, message):
        """Функция авторизации на сервере"""
        # Проверка каждого поля сообщения, если поле есть -> записть данных, если нет -> снятие флага об успешной авторизции и оповещение сервера"""
        if "clientid" in message["data"]: self.clientid = message["data"]["clientid"]
        else: await self.MessageToServer(ws, {"action": "Login", "status": "false", "data": "'clientid' NOT RECEIVED"})
        if "roomname" in message["data"]: self.roomname = message["data"]["roomname"]
        else: await self.MessageToServer(ws, {"action": "Login", "status": "false", "data": "'roomname' NOT RECEIVED"})
        if "name" in message["data"]: self.name = message["data"]["name"]
        else: await self.MessageToServer(ws, {"action": "Login", "status": "false", "data": "'name' NOT RECEIVED"})
        if "apikey" in message["data"]: self.apikey = message["data"]["apikey"]
        else: await self.MessageToServer(ws, {"action": "Login", "status": "false", "data": "'apikey' NOT RECEIVED"})
        # Если одно из полей сообщения авторизации не пришло -> переавторизация"""
        if self.clientid != "" and self.roomname != "" and self.name != "" and self.apikey != "":
            await self.MessageToServer(ws, {"data": "SUCCESS LOGIN"})
        else:
            await self.MessageToServer(ws, {"action": "Login", "login": self.login, "password": self.password, "roomid": self.roomid})
            await asyncio.sleep(1) # таймер чтобы не отправлять сообщение об переавторизации слишком быстро

    async def SetConfig(self, ws, message):
        """Функция установки config на маяки"""
        if self.start_flag: await self.Stop(ws) # если нода уже работает, а новый конфиг пришел -> останавливаем работу ноды
        self.config = message["data"]
        success_set_config_flag = True # флаг об успешной установке config
        for config in self.config:
            # Проверка каждого поля сообщения, если данных нет -> снятие флага об успешной утсановке config и оповещение сервера"""
            if not "IP" in config:
                success_set_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'IP' RECEIVED IN CONFIG: {str(config)}"})
            if not "NUMBER" in config:
                success_set_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'NUMBER' RECEIVED IN CONFIG: {str(config)}"})
            if not "ADRX" in config:
                success_set_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'ADRX' RECEIVED IN CONFIG: {str(config)}"})
            if not "ADTX" in config:
                success_set_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'ADTX' RECEIVED IN CONFIG: {str(config)}"})
            if not "X" in config:
                success_set_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'X' RECEIVED IN CONFIG: {str(config)}"})
            if not "Y" in config:
                success_set_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'Y' RECEIVED IN CONFIG: {str(config)}"})
            if not "Z" in config:
                success_set_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'Z' RECEIVED IN CONFIG: {str(config)}"})
            if not "ROLE" in config:
                success_set_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'ROLE' RECEIVED IN CONFIG: {str(config)}"})
            if not "MASTER_NUMBER" in config:
                success_set_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'MASTER_NUMBER' RECEIVED IN CONFIG: {str(config)}"})
            if not "LAG" in config:
                success_set_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'LAG' RECEIVED IN CONFIG: {str(config)}"})

        if success_set_config_flag:
            """Так как соединение маяков и ноды происходит по socket-соединению, то разрывать его нельзя, поэтому необходимо написать обработчик конфигурации и переконфигарация старых(неактивных) и новых(активных) маяков"""
            """Цикл для проверки: есть ли уже в активных на ноде маяках тех, которых нет в новом config, если нет -> переводим маяк в неактвное состояние, если есть такой же маяк и в новом config, и в уже активных -> переконфигурция маяка"""
            for anchor in reversed(self.enabled_anchors): # reversed - для того чтобы при удалении старого маяка из массива не нарушался его перебор в цикле
                disable_anchor_flag = True # флаг проверки неактивного маяка
                for config in reversed(self.config): # reversed - для того чтобы при удалении старого маяка из массива не нарушался его перебор в цикле
                    if anchor.IP == config["IP"]: # сравнение двух ip-адресов
                        disable_anchor_flag = False # отключение флага если тот же маяк есть
                        await anchor.Reconfig(config)  # переконфигурация
                if disable_anchor_flag: # если флаг остался -> перевод маяка в неактивный режим
                    self.disabled_anchors.append(anchor) # добавление маяка в массив неактивных маяков
                    self.enabled_anchors.remove(anchor) # удаление маяка из массива активных маяков
                    print("OLD ANCHOR " + str(anchor.IP) + " DISABLED")
            """Цикл для добавления новых маяков из config"""
            for config in reversed(self.config): # reversed - для того чтобы при удалении старого маяка из массива не нарушался его перебор в цикле
                new_anchor_flag = True # флаг для проверки наличия нового маяка
                for anchor in reversed(self.enabled_anchors):  # reversed - для того чтобы при удалении старого маяка из массива не нарушался его перебор в цикле
                    if anchor.IP == config["ip"]:
                        new_anchor_flag = False # отключение флага если такой же маяк есть
                if new_anchor_flag: # если флаг остался -> в config и в массиве активных маяков нет похожего
                    if self.disabled_anchors: # проверка есть ли неактивные маяки, если есть -> ищем новый маяк в массиве неактивных маяков
                        disable_anchor_flag = True # флаг для проверки наличия нового маяка в массиве неактивных маяков
                        """Цикл для проверки есть ли новых маяк из config в неактвных маяках -> если есть добавление его в общий массив и переконфигурация"""
                        for anchor in reversed(self.disabled_anchors): # reversed - для того чтобы при удалении старого маяка из массива не нарушался его перебор в цикле
                            if anchor.IP == config["IP"]:
                                disable_anchor_flag = False # отключение флага если такой же маяк есть
                                await anchor.Reconfig(config) # переконфигурация
                                self.enabled_anchors.append(anchor) # добавление маяка в массив активных маяков
                                self.disabled_anchors.remove(anchor) # удаление маяка из массива неактивных маяков
                        if disable_anchor_flag: # если флаг не отключился -> маяк новый
                            anchor = Anchor(config) # экземпляр класса маяка
                            self.enabled_anchors.append(anchor)  # добавление маяка в массив активных маяков
                    else: # если массив с неактивными маяками пустой -> маяк точно новый
                        anchor = Anchor(config) # экземпляр класса маяка
                        if anchor.socket_flag: # добавление маяка в массив только если открылось socket-соединение
                            self.enabled_anchors.append(anchor) # добавление маяка в массив активных маяков

            if self.rf_config_flag: # если с сервера уже приходил rf_config -> устанавливаем его
                for anchor in self.enabled_anchors: await anchor.SetRfConfig(self.rf_config)
            self.config_flag = True # активация флага наличия config
            await self.MessageToServer(ws, {"data": "SUCCESS SET CONFIG -> NODE HAVE " + str(len(self.enabled_anchors)) + " ACTIVE ANCHORS"})

    async def SetRfConfig(self, ws, message):
        """Функция установки rf_config на маяки"""
        if self.start_flag: await self.Stop(ws)
        error_format_flag = False
        try: self.rf_config = message["data"][0] # rf_config для маяков (приходит с сервера), [0], т.к. rf_config лежит в 0 элементе массива [{rf_config}]
        except:
            error_format_flag = True
            await self.MessageToServer(ws, {"data": "ERROR FORMAT"})
        if not error_format_flag:
            """Проверка на пустые поля"""
            success_set_rf_config_flag = True
            # Проверка каждого поля сообщения, если данных нет -> снятие флага об успешной утсановке rg_config и оповещение сервера"""
            if not "chnum" in self.rf_config:
                success_set_rf_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'chnum' RECEIVED IN RF CONFIG"})
            if not "prf" in self.rf_config:
                success_set_rf_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'prf' RECEIVED IN RF CONFIG"})
            if not "datarate" in self.rf_config:
                success_set_rf_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'datarate' RECEIVED IN RF CONFIG"})
            if not "preamblecode" in self.rf_config:
                success_set_rf_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'preamblecode' RECEIVED IN RF CONFIG"})
            if not "preamblelen" in self.rf_config:
                success_set_rf_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'preamblelen' RECEIVED IN RF CONFIG"})
            if not "pac" in self.rf_config:
                success_set_rf_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'pac' RECEIVED IN RF CONFIG"})
            if not "nsfd" in self.rf_config:
                success_set_rf_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'nsfd' RECEIVED IN RF CONFIG"})
            if not "diagnostic" in self.rf_config:
                success_set_rf_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'diagnostic' RECEIVED IN RF CONFIG"})
            if not "lag" in self.rf_config:
                success_set_rf_config_flag = False
                await self.MessageToServer(ws, {"data": f"NOT 'lag' RECEIVED IN RF CONFIG"})

            if success_set_rf_config_flag:
                if self.config_flag: # установка rf_config возможна только если уже есть config, поэтому проверяем это условие
                    for anchor in self.enabled_anchors: await anchor.SetRfConfig(self.rf_config) # установка rf_config
                self.rf_config_flag = True # активация флага наличия rf_config
                await self.MessageToServer(ws, {"data": "SUCCESS SET RF CONFIG"})

    async def Start(self, ws):
        """Функция запуска ноды"""
        if self.config_flag and self.rf_config_flag: # старт возможен только если уже пришли config и rf_config, поэтому проверяем это условие
            for anchor in self.enabled_anchors: await anchor.StartSpam() # запуск спама сообщений от маяков
            for anchor in self.enabled_anchors: self.anchors_tasks.append(asyncio.create_task(anchor.AnchorHandler(self.log_buffer))) # добавление функции обработки маяка в массив задач маяков и асинхронный запуск этих функций
            self.start_flag = True # включене флага проверки рабочего состояния ноды
            self.stop_flag = False # выключене флага проверки нерабочего состояния ноды
            await self.MessageToServer(ws, {"data": "NODE START"})
            # await self.MessageToServer(ws, {"action": "RoomConfig", "apikey": self.apikey, "clientid": self.clientid, "organization": self.clientid, "roomid": self.roomid, "anchors": self.config})
        if not self.config_flag: await self.MessageToServer(ws, {"data": "NEED CONFIG"})
        if not self.rf_config_flag: await self.MessageToServer(ws, {"data": "NEED RF_CONFIG"})

    async def Stop(self, ws):
        """Функция остановки ноды"""
        for anchor in self.enabled_anchors: await anchor.Stop() # остановка спама сообщений от маяков
        for task in reversed(self.anchors_tasks): # reversed - для того чтобы при удалении старой задачи из массива не нарушался его перебор в цикле
            task.cancel() # отмена асинхронных задачи маяка
            self.anchors_tasks.remove(task) # удаление задачи из массива асинхронных задач для маяков
        self.start_flag = False # выключене флага проверки рабочего состояния ноды
        self.stop_flag = True # включене флага проверки нерабочего состояния ноды
        await self.MessageToServer(ws, {"data": "NODE STOP"})

def NodeConfigRead():
    """Функция чтения данных о ноде из текстового файла"""
    login, password, roomid, server_ip, server_port = "", "", "", "", ""
    f = open("NODE_CONFIG.txt", "r")
    while True:
        line = f.readline().split()
        if not line or len(line) < 3: break
        else:
            if line[0] == "login": login = str(line[2])
            if line[0] == "password": password = str(line[2])
            if line[0] == "roomid": roomid = str(line[2])
            if line[0] == "server_ip": server_ip = str(line[2])
            if line[0] == "server_port": server_port = str(line[2])
    f.close()
    return login, password, roomid, server_ip, server_port

def StopAnchors(node):
    """Функция остановки маяков после разрыва соединения с сервером"""
    for anchor in node.enabled_anchors:
        try:
            anchor.socket.sendall(rm.build_RTLS_START_REQ(0))  # остановка спама сообщений от маяков
            print(f"ANCHOR NUMBER {anchor.number} WITH NAME {anchor.name} [IP: {anchor.IP} ] STOP")
        except: print("ERROR STOP ANCHORS")
    for task in reversed(node.anchors_tasks): # reversed - для того чтобы при удалении старой задачи из массива не нарушался его перебор в цикле
        task.cancel() # отмена асинхронных задачи маяка
        node.anchors_tasks.remove(task) # удаление задачи из массива асинхронных задач для маяков
    print("NODE STOP")
    node.start_flag = False # выключение флага проверки рабочего состояния ноды
    node.stop_flag = True # включение флага проверки нерабочего состояния ноды
    node.log_buffer = []


if __name__ == '__main__':
    while True: # бесконечный цикл для чтения данных о ноде из текстового файла, если данные получены -> выход из цикла, если нет -> перезапуск
        try: # попытка чтения данных о ноде из текстого файла
            login, password, roomid, server_ip, server_port = NodeConfigRead()
            if login != "" and password != "" and roomid != "" and server_ip != "" and server_port != "": break # если все данные о ноде записаны -> выход из цикла
            else: print
        except: # сообщение об ошибке, если ("ERROR IN NODE CONFIG")файл не открылся или прочитался не корректно
            print("ERROR READ CONFIG FILE")
    node = Node(login, password, roomid, server_ip, server_port) # экземпляр класса ноды
    loop = asyncio.get_event_loop() # асинхронная петля
    """Запуск бесконечной работы ноды, если сервер не отвечает -> пробует подсоединиться еще раз"""
    while True:
        try: loop.run_until_complete(node.NodeHandler()) # запуск асинхронной петли -> функции обработки ноды
        except KeyboardInterrupt: break # отслеживание исключения при ручном отключении ноды CTRL + C, если сработало -> выход из работы
        except: # отслеживания всех остальных исключений, если сработало -> запуск производится еще раз
            if node.start_flag: # если нода работала
                StopAnchors(node)
            print('ERROR SERVER CONNECT -> TRY AGAIN')