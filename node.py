import websockets
import asyncio
import json
import reports_and_messages as rm
from anchor import Anchor


"""Класс ноды"""
class Node:

    def __init__(self, login, password, roomid, server_ip, server_port):
        self.server_ip = server_ip       # ip-адрес сервера
        self.server_port = server_port   # порт сервера
        self.login = login               # логин ноды
        self.password = password         # пароль ноды
        self.apikey = ""                 # apikey - ключ безопасности для общения с сервером
        self.roomid = roomid             # ID комнаты, где установлена нода
        self.clientid = ""               # ID клиента
        self.roomname = ""               # название комнаты
        self.name = ""                   # название организации
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


    async def message_to_server(self, ws, message):
        await ws.send(json.dumps(message)) # отправка сообщения на сервер
        print("MESSAGE TO SERVER: " + str(message))

    """Функция обработки ноды"""
    async def node_handler(self):
        url = f"ws://{self.server_ip}:{self.server_port}" # url-адрес сервера
        async with websockets.connect(url, ping_interval=None) as ws: # открытие подключения к серверу
            print("NODE CONNECTED TO SERVER: " + str(self.server_ip) + ":" + str(self.server_port))
            login_message = {"action": "Login", "login": self.login, "password": self.password, "roomid": self.roomid}
            await self.message_to_server(ws, login_message)
            await asyncio.gather(self.node_produce(ws), self.node_receive(ws)) # запуск асинхронной работы приемной и передающей функций ноды

    """Функция передачи ноды"""
    async def node_produce(self, ws):
        while True: # запуск бесконечного цикла для непрерывной работы функции
            if self.log_buffer: # если массив сообщений не пустой -> отправляет сообщения на сервер
                message = self.log_buffer.pop(0) # взятие первого сообщения и его удаление из массива
                message["sender"] = str(hex(message["sender"][1])[2:]) + str(hex(message["sender"][0])[2:]) # для корректной отправки данных в формате JSON заменяем байтовое поле с названием маяка на его сокращенное название типа str
                message["receiver"] = str(hex(message["receiver"][1])[2:]) + str(hex(message["receiver"][0])[2:])# для корректной отправки данных в формате JSON заменяем байтовое поле с названием маяка на его сокращенное название типа str
                log_message = {"action": "Log", "apikey": self.apikey, "organization": self.clientid ,"name": self.name, "info": "log message", "roomid": self.roomid, "status": "true", "data": message} # сообщение типа Log для оптравки на сервер
                await self.message_to_server(ws, log_message)
            await asyncio.sleep(0.01) # чтобы у других функций было время для работы в асинхронном режиме, функция передачи засыпает на определенное время в цикле и передает право на работу другим функциям

    """Функция приема ноды"""
    async def node_receive(self, ws):
        while True: # запуск бесконечного цикла для непрерывной работы функции
            message = json.loads(await ws.recv()) # прием сообщения от сервера
            print("MESSAGE FROM SERVER " + str(message))
            # если статус false - печать предупреждающего соощдения
            if "status" in message:
                if message["status"] == "false":
                    print("---WARNING--- " + str(message["data"]) + " ---WARNING---")
                elif "action" in message and message["status"] == "true":
                    # обработка авторизации
                    if message["action"] == "Login" and message["status"] == "true":
                        await self.login_on_the_server(ws, message)
                    # обработка установки config
                    elif message["action"] == "SetConfig" and message["status"] == "true":
                        await self.set_config(ws, message)
                    # обаботка установки rf_config
                    elif message["action"] == "SetRfConfig" and message["status"] == "true":
                        await self.set_rf_config(ws, message)
                    # обработка команды start
                    elif message["action"] == "Start" and message["status"] == "true":
                        await self.start(ws)
                    # обработка команды stop
                    elif message["action"] == "Stop" and message["status"] == "true":
                        await self.stop(ws)

    """Функция авторизации на сервере"""
    async  def login_on_the_server(self, ws, message):
        error_login_flag = False
        if "data" in message: # проверка есть ли поле "action" в сообщении
            # проверка есть ли поле "clientid" в сообщении
            if "clientid" in message["data"]:
                self.clientid = message["data"]["clientid"] # ID клиента
                print("clientid: " + self.clientid)
            else:
                error_login_flag = True
                print("clientid NOT RECIEVED")
                notrecieved_clientid_message = {"action": "Login", "status": "false", "data": "clientid NOT RECIEVED"}
                await self.message_to_server(ws, notrecieved_clientid_message)
            # проверка есть ли поле "roomname" в сообщении
            if "roomname" in message["data"]:
                self.roomname = message["data"]["roomname"] # Название комнаты
                print("roomname: " + self.roomname)
            else:
                error_login_flag = True
                print("roomname NOT RECIEVED")
                notrecieved_roomid_message = {"action": "Login", "status": "false", "data": "roomname NOT RECIEVED"}
                await self.message_to_server(ws, notrecieved_roomid_message)
            # проверка есть ли поле "name" в сообщении
            if "name" in message["data"]:
                self.name = message["data"]["name"]  # Название организации
                print("name: " + self.name)
            else:
                error_login_flag = True
                print("name NOT RECIEVED")
                notrecieved_name_message = {"action": "Login", "status": "false", "data": "name NOT RECIEVED"}
                await self.message_to_server(ws, notrecieved_name_message)
            # проверка есть ли поле "apikey" в сообщении
            if "apikey" in message["data"]:
                self.apikey = message["data"]["apikey"]  # apikey - ключ безопасности для общения с сервером
                print("APIKEY: " + self.apikey)
            else:
                error_login_flag = True
                print("APIKEY NOT RECIEVED")
                notrecieved_apikey_message = {"action": "Login", "status": "false", "data": "APIKEY NOT RECIEVED"}
                await self.message_to_server(ws, notrecieved_apikey_message)

        else:
            error_login_flag = True
            print("data NOT RECIEVED")
            notrecieved_data_message = {"action": "Login", "status": "false", "data": "data NOT RECIEVED"}
            await self.message_to_server(ws, notrecieved_data_message)

        """Если одно из полей данных для ноды не пришло -> отправка сообщения об авторизации на сервер еще раз"""
        if error_login_flag:
            login_message = {"action": "Login", "login": self.login, "password": self.password, "roomid": self.roomid}
            await self.message_to_server(ws, login_message)
            await asyncio.sleep(3)
        else:
            success_login_messsage = {"data": "SUCCESS LOGIN"}
            await self.message_to_server(ws, success_login_messsage)

    """Функция установки config"""
    async def set_config(self, ws, message):
        if "data" in message:
            self.config = message["data"] # config для маяков (приходит с сервера)
            if self.start_flag: await self.stop(ws) # если нода уже работает, а новый конфиг пришел -> останавливаем работу ноды
            """Обработчик пустых полей"""
            error_config_flag = False
            i = 0 # счетчик для определения в каком конфиге ошибка пустого поля
            for config in reversed(self.config):
                # проверка есть ли поле "ip" в config
                if not "ip" in config:
                    error_config_flag = True
                    print(f"NOT 'IP' RECIEVED IN CONFIG {len(self.config) - i}")
                    not_recieved_ip_recieved_message = {f"NOT 'IP' RECIEVED IN CONFIG {len(self.config) - i}"}
                    await self.message_to_server(ws, not_recieved_ip_recieved_message)
                # проверка есть ли поле "number" в config
                if not "number" in config:
                    error_config_flag = True
                    print(f"NOT 'number' RECIEVED IN CONFIG {len(self.config) - i}")
                    not_recieved_number_message = {f"NOT 'number' RECIEVED IN CONFIG {len(self.config) - i}"}
                    await self.message_to_server(ws, not_recieved_number_message)
                # проверка есть ли поле "adrx" в config
                if not "adrx" in config:
                    error_config_flag = True
                    print(f"NOT 'adrx' RECIEVED IN CONFIG {len(self.config) - i}")
                    not_recieved_adrx_message = {f"NOT 'adrx' RECIEVED IN CONFIG {len(self.config) - i}"}
                    await self.message_to_server(ws, not_recieved_adrx_message)
                # проверка есть ли поле "adtx" в config
                if not "adtx" in config:
                    error_config_flag = True
                    print(f"NOT 'adtx' RECIEVED IN CONFIG {len(self.config) - i}")
                    not_recieved_adtx_message = {f"NOT 'adtx' RECIEVED IN CONFIG {len(self.config) - i}"}
                    await self.message_to_server(ws, not_recieved_adtx_message)
                # проверка есть ли поле "x" в config
                if not "x" in config:
                    error_config_flag = True
                    print(f"NOT 'x' RECIEVED IN CONFIG {len(self.config) - i}")
                    not_recieved_x_message = {f"NOT 'x' RECIEVED IN CONFIG {len(self.config) - i}"}
                    await self.message_to_server(ws, not_recieved_x_message)
                # проверка есть ли поле "y" в config
                if not "y" in config:
                    error_config_flag = True
                    print(f"NOT 'y' RECIEVED IN CONFIG {len(self.config) - i}")
                    not_recieved_y_message = {f"NOT 'y' RECIEVED IN CONFIG {len(self.config) - i}"}
                    await self.message_to_server(ws, not_recieved_y_message)
                # проверка есть ли поле "z" в config
                if not "z" in config:
                    error_config_flag = True
                    print(f"NOT 'z' RECIEVED IN CONFIG {len(self.config) - i}")
                    not_recieved_z_message = {f"NOT 'z' RECIEVED IN CONFIG {len(self.config) - i}"}
                    await self.message_to_server(ws, not_recieved_z_message)
                # проверка есть ли поле "role" в config
                if not "role" in config:
                    error_config_flag = True
                    print(f"NOT 'role' RECIEVED IN CONFIG {len(self.config) - i}")
                    not_recieved_role_message = {f"NOT 'role' RECIEVED IN CONFIG {len(self.config) - i}"}
                    await self.message_to_server(ws, not_recieved_role_message)
                # проверка есть ли поле "masternumber" в config
                if not "masternumber" in config:
                    error_config_flag = True
                    print(f"NOT 'masternumber' RECIEVED IN CONFIG {len(self.config) - i}")
                    not_recieved_masternumber_message = {f"NOT 'masternumber' RECIEVED IN CONFIG {len(self.config) - i}"}
                    await self.message_to_server(ws, not_recieved_masternumber_message)
                # проверка есть ли поле "lag" в config
                if not "lag" in config:
                    error_config_flag = True
                    print(f"NOT 'lag' RECIEVED IN CONFIG {len(self.config) - i}")
                    not_recieved_lag_message = {f"NOT 'lag' RECIEVED IN CONFIG {len(self.config) - i}"}
                    await self.message_to_server(ws, not_recieved_lag_message)
                i += 1

            if not error_config_flag:
                """Так как соединение маяков и ноды происходит по socket-соединению, то разрывать его нельзя, поэтому необходимо написать обработчик конфигурации и переконфигарация старых(неактивных) и новых(активных) маяков"""

                """Цикл для проверки: есть ли уже в активных на ноде маяках тех, которых нет в новом config, если нет -> переводим маяк в неактвное состояние, если есть такой же маяк и в новом config, и в уже активных -> переконфигурция маяка"""
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
                for config in reversed(self.config): # reversed - для того чтобы при удалении старого маяка из массива не нарушался его перебор в цикле
                    new_anchor_flag = True # флаг для проверки наличия нового маяка
                    for anchor in reversed(self.enabled_anchors):  # reversed - для того чтобы при удалении старого маяка из массива не нарушался его перебор в цикле
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
                                    self.disabled_anchors.remove(anchor) # удаление маяка из массива неактивных маяков
                            if disable_anchor_flag: # если флаг не отключился -> маяк новый
                                anchor = Anchor(config) # экземпляр класса маяка
                                self.enabled_anchors.append(anchor)  # добавление маяка в массив активных маяков
                        else: # если массив с неактивными маяками пустой -> маяк точно новый
                            anchor = Anchor(config) # экземпляр класса маяка
                            if anchor.socket_flag: # добавление маяка в массив только если открылось socket-соединение
                                self.enabled_anchors.append(anchor) # добавление маяка в массив активных маяков

                if self.rf_config_flag: # если с сервера уже приходил rf_config -> устанавливаем его
                    for anchor in self.enabled_anchors:
                        await anchor.set_rf_config(self.rf_config) # установка rf_config
                        print(anchor.IP + " SET RF_CONFIG")

                self.config_flag = True # активация флага наличия config
                print("NODE HAVE " + str(len(self.enabled_anchors)) + " ACTIVE ANCHORS")
                success_set_config_message = {"data": "SUCCESS SET CONFIG -> NODE HAVE " + str(len(self.enabled_anchors)) + " ACTIVE ANCHORS"}
                await self.message_to_server(ws, success_set_config_message)
            else:
                print("ERROR RECIEVE IN CONFIG DATA")
                error_recieve_in_config_data_message = {"ERROR RECIEVE IN CONFIG DATA"}
                await self.message_to_server(ws, error_recieve_in_config_data_message)
        else:
            print("NOT RECIEVED DATA CONFIG")
            notrecieved_data_config_message = {"action": "SetConfig", "status": "false", "data": "NOT RECIEVED DATA CONFIG"}
            await self.message_to_server(ws, notrecieved_data_config_message)

    """Функция установки rf_config"""
    async def set_rf_config(self, ws, message):
        if self.start_flag: await self.stop(ws)
        if "data" in message:
            error_format_flag = False
            try:
                self.rf_config = message["data"][0] # rf_config для маяков (приходит с сервера), [0], т.к. rf_config лежит в 0 элементе массива [{rf_config}]
            except:
                error_format_flag = True
                print("ERROR FORMAT")
                error_format_message = {"ERROR FORMAT"}
                await self.message_to_server(ws, error_format_message)
            if not error_format_flag:
                """Проверка на пустые поля"""
                error_rf_config_flag = False
                # проверка есть ли поле "chnum" в rf config
                if not "chnum" in self.rf_config:
                    error_rf_config_flag = True
                    print(f"NOT 'chnum' RECIEVED IN RF CONFIG")
                    not_recieved_chnum_message = {f"NOT 'chnum' RECIEVED IN RF CONFIG"}
                    await self.message_to_server(ws, not_recieved_chnum_message)
                # проверка есть ли поле "prf" в rf config
                if not "prf" in self.rf_config:
                    error_rf_config_flag = True
                    print(f"NOT 'prf' RECIEVED IN RF CONFIG")
                    not_recieved_prf_message = {f"NOT 'prf' RECIEVED IN RF CONFIG"}
                    await self.message_to_server(ws, not_recieved_prf_message)
                # проверка есть ли поле "datarate" в rf config
                if not "datarate" in self.rf_config:
                    error_rf_config_flag = True
                    print(f"NOT 'datarate' RECIEVED IN RF CONFIG")
                    not_recieved_datarate_message = {f"NOT 'datarate' RECIEVED IN RF CONFIG"}
                    await self.message_to_server(ws, not_recieved_datarate_message)
                # проверка есть ли поле "preamblecode" в rf config
                if not "preamblecode" in self.rf_config:
                    error_rf_config_flag = True
                    print(f"NOT 'preamblecode' RECIEVED IN RF CONFIG")
                    not_recieved_preamblecode_message = {f"NOT 'preamblecode' RECIEVED IN RF CONFIG"}
                    await self.message_to_server(ws, not_recieved_preamblecode_message)
                # проверка есть ли поле "preamblelen" в rf config
                if not "preamblelen" in self.rf_config:
                    error_rf_config_flag = True
                    print(f"NOT 'preamblelen' RECIEVED IN RF CONFIG")
                    not_recieved_preamblelen_message = {f"NOT 'preamblelen' RECIEVED IN RF CONFIG"}
                    await self.message_to_server(ws, not_recieved_preamblelen_message)
                # проверка есть ли поле "pac" в rf config
                if not "pac" in self.rf_config:
                    error_rf_config_flag = True
                    print(f"NOT 'pac' RECIEVED IN RF CONFIG")
                    not_recieved_pac_message = {f"NOT 'pac' RECIEVED IN RF CONFIG"}
                    await self.message_to_server(ws, not_recieved_pac_message)
                # проверка есть ли поле "nsfd" в rf config
                if not "nsfd" in self.rf_config:
                    error_rf_config_flag = True
                    print(f"NOT 'nsfd' RECIEVED IN RF CONFIG")
                    not_recieved_nsfd_message = {f"NOT 'nsfd' RECIEVED IN RF CONFIG"}
                    await self.message_to_server(ws, not_recieved_nsfd_message)
                # проверка есть ли поле "diagnostic" в rf config
                if not "diagnostic" in self.rf_config:
                    error_rf_config_flag = True
                    print(f"NOT 'diagnostic' RECIEVED IN RF CONFIG")
                    not_recieved_diagnostic_message = {f"NOT 'diagnostic' RECIEVED IN RF CONFIG"}
                    await self.message_to_server(ws, not_recieved_diagnostic_message)
                # проверка есть ли поле "lag" в rf config
                if not "lag" in self.rf_config:
                    error_rf_config_flag = True
                    print(f"NOT 'lag' RECIEVED IN RF CONFIG")
                    not_recieved_lag_message = {f"NOT 'lag' RECIEVED IN RF CONFIG"}
                    await self.message_to_server(ws, not_recieved_lag_message)

                if not error_rf_config_flag:
                    if self.config_flag: # установка rf_config возможна только если уже есть config, поэтому проверяем это условие
                        for anchor in self.enabled_anchors:
                            await anchor.set_rf_config(self.rf_config) # установка rf_config
                            print(anchor.IP + " SET RF_CONFIG")
                    self.rf_config_flag = True # активация флага наличия rf_config
                    success_set_rf_config_message = {"data": "SUCCESS SET RF CONFIG"}
                    await self.message_to_server(ws, success_set_rf_config_message)
                else:
                    print("ERROR RECIEVE IN RF CONFIG DATA")
                    error_recieve_in_rf_config_data = {"ERROR RECIEVE IN RF CONFIG DATA"}
                    await self.message_to_server(ws, error_recieve_in_rf_config_data)
        else:
            print("NOT RECIEVED DATA RF CONFIG")
            notrecieved_data_rf_config_message = {"action": "SetConfig", "status": "false", "data": "NOT RECIEVED DATA RF CONFIG"}
            await self.message_to_server(ws, notrecieved_data_rf_config_message)

    """Функция установки команды start"""
    async def start(self, ws):
        if self.config_flag and self.rf_config_flag: # старт возможен только если уже пришли config и rf_config, поэтому проверяем это условие
            for anchor in self.enabled_anchors: # пробежка по элементам общего массива маяков
                await anchor.start_spam() # запуск спама сообщений от маяков
            for anchor in self.enabled_anchors: # пробежка по элементам общего массива маяков
                self.anchors_tasks.append(asyncio.create_task(
                    anchor.anchor_handler(self.log_buffer))) # добавление функции обработки маяка в массив задач маяков и асинхронный запуск этих функций
            print("NODE START")
            success_start_node_message = {"data": "NODE START"}
            await self.message_to_server(ws, success_start_node_message)

        if not self.config_flag: # проверка наличия config
            need_config_message = {"action": "start", "status": "false", "apikey": self.apikey, "data": "NEED CONFIG"}
            await self.message_to_server(ws, need_config_message)
        if not self.rf_config_flag: # проверка наличия rf_config
            need_rf_config_message = {"action": "start", "status": "false", "apikey": self.apikey, "data": "NEED RF_CONFIG"}
            await self.message_to_server(ws, need_rf_config_message)

        if self.config_flag and self.rf_config_flag:
            self.start_flag = True # включене флага проверки рабочего состояния ноды
            self.stop_flag = False # выключене флага проверки нерабочего состояния ноды

    """Функция установки команды stop"""
    async def stop(self, ws):
        for anchor in self.enabled_anchors:
            await anchor.stop() # остановка спама сообщений от маяков
        for task in reversed(self.anchors_tasks): # reversed - для того чтобы при удалении старой задачи из массива не нарушался его перебор в цикле
            task.cancel() # отмена асинхронных задачи маяка
            self.anchors_tasks.remove(task) # удаление задачи из массива асинхронных задач для маяков
        self.start_flag = False # выключене флага проверки рабочего состояния ноды
        self.stop_flag = True # включене флага проверки нерабочего состояния ноды
        success_stop_node_message = {"data": "NODE STOP"}
        await self.message_to_server(ws, success_stop_node_message)
        print("NODE STOP")


"""Главная функция включения ноды"""
if __name__ == '__main__':
    login = "TestOrg"          # логин ноды
    password = "TestOrgPass"   # пароль ноды
    roomid = "1"               # ID комнаты, где установлена нода
    # server_ip = "127.0.0.1"    # ip-адрес сервера
    server_ip = "10.3.168.123"
    server_port = "9000"       # порт сервера
    node = Node(login, password, roomid, server_ip, server_port) # экземпляр класса ноды
    loop = asyncio.get_event_loop() # асинхронная петля

    """Запуск бесконечной работы ноды, если сервер не отвечает -> пробует подсоединиться еще раз"""
    start_work_flag = True # флаг работы ноды
    while start_work_flag:
        try:
            start_work_flag = False # отключения флага если работа началась
            loop.run_until_complete(node.node_handler()) # запуск асинхронной петли -> функции обработки ноды
        except KeyboardInterrupt: # отслеживание исключения при ручном отключении ноды CTRL + C, если сработало -> выход из работы
            print("EXIT")
        except: # отслеживания всех остальных исключений, если сработало -> запуск производится еще раз
            if node.start_flag:
                try:
                    """Остановка маяков"""
                    for anchor in node.enabled_anchors:
                        anchor.socket.sendall(rm.build_RTLS_START_REQ(0))  # остановка спама сообщений от маяков
                    for task in reversed(node.anchors_tasks):  # reversed - для того чтобы при удалении старой задачи из массива не нарушался его перебор в цикле
                        task.cancel()  # отмена асинхронных задачи маяка
                        node.anchors_tasks.remove(task)  # удаление задачи из массива асинхронных задач для маяков
                    print("NODE STOP")
                    node.start_flag = False  # выключение флага проверки рабочего состояния ноды
                    node.stop_flag = True  # включение флага проверки нерабочего состояния ноды
                    """---------------------------------------------------------------------------------------------------------------------------------------"""
                except:
                    print("ERROR STOP ANCHORS")
            start_work_flag = True # включение флага -> цикл запускается еще раз
            print('ERROR SERVER CONNECT -> TRY AGAIN')