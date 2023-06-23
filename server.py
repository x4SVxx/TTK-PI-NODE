import websockets
import asyncio
import json
import string
from client_node import Client_node
from client_client import Client_client
import secrets
import random
import math_client


"""Каждое сообщение посылаемое на сервер должно соответствовать структуре"""
"""{"action": ..., "status": ..., "data": ...}"""
"""
    Типы action:
        Login - аторизация ноды
        Login_client - авторизация клиента
        SetConfig - установить config на ноду
        SetRfConfig - утсановить rf_config на ноду
        Start - запустить ноду
        Stop - остановить ноду
        Log - отправить лог клиенту
"""

"""Загрузка базы данных нод из JSON файла"""
with open('BD_nodes.json') as BD_NODES:
    BD_DATA_NODES = json.load(BD_NODES)

"""Загрузка базы данных клиентов из JSON файла"""
with open('BD_clients.json') as BD_CLIENTS:
    BD_DATA_CLIENTS = json.load(BD_CLIENTS)


"""Функция генерации apikey - ключа безопасности для общения с нодой"""
def generate_apikey():
    letters_and_digits = string.ascii_letters + string.digits
    apikey = ''.join(secrets.choice(letters_and_digits) + str(i) for i in range(15))
    return apikey


"""Класс сервера"""
class Server:
    def __init__(self):
        self.authorized_nodes = [] # массив с авторизированными нодами
        self.authorized_clients = [] # массив с авторизированными клиентами

    """Функция обработки сервера"""
    async def server_handler(self, ws):
        while True:
            try:
                message = json.loads(await ws.recv())  # прием сообщения от пользователя
                """Проверка пришло ли сообщение от уже авторизированного пользователя"""
                authorization_node_flag = False # флаг авторизации ноды
                authorization_client_flag = False # флаг авторизации клиента
                for node in self.authorized_nodes: # пробежка по элементам массива с авторизированными нодами
                    if ws == node.ws:  # сравнение двух websocket-соединений
                        authorization_node_flag = True # активация флага авторизации
                        print("MESSAGE FROM NODE " + node.roomid + " " + str(message))
                        for client in self.authorized_clients:
                            if client.clientid == node.clientid:
                                await client.ws.send(json.dumps(message))
                for client in self.authorized_clients: # пробежка по элементам массива с авторизированными клиентами
                    if ws == client.ws:  # сравнение двух websocket-соединений
                        authorization_client_flag = True # активация флага авторизации
                        print("MESSAGE FROM CLIENT " + client.clientid + " " + str(message))
                if not authorization_node_flag and not authorization_client_flag: # если флаг не сработал - сообщение от неизвестного пользователя
                    print("MESSAGE FROM UNKNOW USER: " + str(message))


                if "action" in message:
                    if message["action"] == "Login": # обтаботка авторизации ноды
                        await self.login_node(message, ws)

                    elif message["action"] == "Login_client": # обработка авторизации клиента
                        await self.login_client(message, ws)

                    elif message["action"] == "Log" and message["status"] == "true": # обработка логирования
                        for node in self.authorized_nodes: # пробежка по элементам массива авторизированных нод
                            if node.apikey == message["apikey"]: # сравнение apikey, если имеется схожий - прием логирования
                                print("Log from node " + node.roomid + " " + str(message["data"]))
                                for client in self.authorized_clients:
                                    if client.clientid == node.clientid:
                                        try:
                                            await client.ws.send(json.dumps(message))
                                        except:
                                            pass
                                        break

                    elif message["action"] == "SetConfig" and message["status"] == "true": # обработка установки config
                        """первый цикл - пробежка по элементам массива с авторизированными клипнтами, второй цикл - пробежка по элементам массива с авторизированными нодами; по apikey находим нужного клиента в массиве, а по его clientid и roomid ноды находим нужную ноду"""
                        for client in self.authorized_clients:
                            if client.apikey == message["apikey"]: # по apikey находим нужного клиента в массиве
                                for node in self.authorized_nodes:
                                    if node.clientid == client.clientid and node.roomid == message["roomid"]: # если clientid и roomid совпали -> свять ноды и соответствующего клиента установлена
                                        await node.ws.send((json.dumps({"action": "SetConfig", "status": "true", "anchors": message["anchors"], "rf_config": message["rf_config"]}))) # отправка сообщения с config на ноду
                                        break

                    elif message["action"] == "SetRfConfig" and message["status"] == "true": # обработка установки rf_config
                        for client in self.authorized_clients:
                            if client.apikey == message["apikey"]:
                                for node in self.authorized_nodes:
                                    if node.clientid == client.clientid and node.roomid == message["roomid"]:
                                        await node.ws.send((json.dumps({"action": "SetRfConfig", "status": "true", "data": message["data"]})))  # отправка сообщения с config на ноду
                                        break

                    elif message["action"] == "Start" and message["status"] == "true": # обработка команды Start
                        for client in self.authorized_clients:
                            if client.apikey == message["apikey"]:
                                # while True:
                                #     await client.ws.send(json.dumps({"action": "Log", "status": "true", "data": {"name": "SD43", "x": random.random()*100, "y": random.random()*100}}))
                                for node in self.authorized_nodes:
                                    if node.clientid == client.clientid and node.roomid == message["roomid"]:
                                        await node.ws.send((json.dumps({"action": "Start", "status": "true", "data": "Start"})))  # отправка сообщения с config на ноду
                                        break

                    elif message["action"] == "Stop" and message["status"] == "true": # обработка команды Stop
                        for client in self.authorized_clients:
                            if client.apikey == message["apikey"]:
                                for node in self.authorized_nodes:
                                    if node.clientid == client.clientid and node.roomid == message["roomid"]:
                                        await node.ws.send((json.dumps({"action": "Stop", "status": "true", "data": "Stop"})))  # отправка сообщения с config на ноду
                                        break
                    elif message["action"] == "SendToMath":
                        if "sn" in message:
                            await self.math_c.ws.send((json.dumps({"action": message["type"], "status": "true", "data": {"organization": message["organization"], "roomid": message["roomid"], "receiver": message['receiver'], "sender": message["sender"], "sn": message["sn"], "timestamp": message["timestamp"]}})))  # отправка сообщения с config на ноду
                        if "seq" in message:
                            await self.math_c.ws.send((json.dumps({"action": message["type"], "status": "true", "data": {"organization": message["organization"], "roomid": message["roomid"], "receiver": message['receiver'], "sender": message["sender"], "seq": message["seq"], "timestamp": message["timestamp"]}})))  # отправка сообщения с config на ноду

                    elif message["action"] == "RoomConfig":
                        await self.math_c.ws.send(json.dumps({"test": "test1"}))
                        await self.math_c.ws.send(json.dumps({"action": 'RoomConfig', "status": "true", "data": {"clientid": message["clientid"], "organization": message["organization"], "roomid": message["roomid"], "anchors": message["anchors"], "ref_tag_config": message["ref_tag_config"]}}))

            except:
                pass
    """Функция авторизации ноды"""
    async  def login_node(self, message, ws):
        reauthorization_flag = False
        """Проверка есть ли уже данная нода в авторизированных"""
        authorization_flag = False # флаг авторизации
        for node in self.authorized_nodes:
            if ws == node.ws: # сравнение двух websocket-соединений
                authorization_flag = True # активация флага авторизации

        """Проверка есть ли поля "status" и "action" в сообщении, если есть и поле "status" равно "false" -> отправляем ноду на переавторизацию"""
        if "status" in message and "action" in message:
            if message["status"] == "false" and message["action"] == "Login":
                if authorization_flag:
                    for node in self.authorized_nodes:
                        if ws == node.ws:  # сравнение двух websocket-соединений
                            self.authorized_nodes.remove(node) # удаление ноды из списка авторизированных нод, затем снятие флага авторизации и отправка на переавторизацию
                authorization_flag = False
                reauthorization_flag = True
        """Сравнение параметров и авторизация ноды"""
        if not authorization_flag and not reauthorization_flag: # если флаг не сработал - отправка ноды на авторизацию
            for number, node in BD_DATA_NODES.items():
                if node["Node_login"] == message["login"] and \
                        node["Node_password"] == message["password"] and\
                        node["Node_roomid"] == message["roomid"]: # сравнение логина, пароля и roomid
                    apikey = generate_apikey() # генерация apikey
                    client_node = Client_node(node["Node_roomid"], node["Node_login"], node["Node_password"], node["Node_clientid"], node["Node_roomname"], node["Organization"], apikey, ws) # экземпляр класса client_node
                    self.authorized_nodes.append(client_node) # добавление ноды в массив авторизированных нод
                    await client_node.ws.send((json.dumps({"action": "Login", "status": "true", "data": {"apikey": apikey, "clientid": node["Node_clientid"], "roomname": node["Node_roomname"], "name": node["Organization"], "organization": node["Organization"]}}))) # отпркавка сообщения об успешной авторизации на ноды и посыл apikey
                    print("NODE AUTHORIZED" + " | " + "Organization: " + str(node["Organization"]) + " | " + "Node ID: " + str(node["Node_roomid"]) + " | " + "roomname: " + str(node["Node_roomname"]) + " | " + "client_id: " + str(node["Node_clientid"]))
                    break
        else: # если флаг сработал - отправка сообщения на ноду об уже имеющейся авторизации
            await ws.send((json.dumps({"action": "login", "status": "false", "data": "You are already authorized"})))
        if message["login"] == "mathLogin":
            self.math_c = math_client.Client_math(message["roomid"], message["login"], message["password"], ws)
            print("math_auto")

    """Функция авторизации клиента"""
    async def login_client(self, message, ws):
        reauthorization_flag = False
        """Проверка есть ли уже данный клиент в авторизированных"""
        authorization_flag = False # флаг авторизации
        for client in self.authorized_clients:
            if ws == client.ws: # сравнение двух websocket-соединений
                authorization_flag = True # активация флага авторизации

        """Проверка есть ли поля "status" и "action" в сообщении, если есть и поле "status" равно "false" -> отправляем клиента на переавторизацию"""
        if "status" in message and "action" in message:
            if message["status"] == "false" and message["action"] == "Login":
                if authorization_flag:
                    for client in self.authorized_nodes:
                        if ws == client.ws:  # сравнение двух websocket-соединений
                            self.authorized_clients.remove(client) # удаление клиента из списка авторизированных клиентов, затем снятие флага авторизации и отправка на переавторизацию
                authorization_flag = False
                reauthorization_flag = True
        """Сравнение параметров и авторизация клиента"""
        if not authorization_flag and not reauthorization_flag: # если флаг не сработал - отправка клиента на авторизацию
            for number, client in BD_DATA_CLIENTS.items():
                if client["Client_login"] == message["login"] and \
                        client["Client_password"] == message["password"]: # сравнение логина и пароля
                    apikey = generate_apikey() # генерация apikey
                    client_client = Client_client(client["Client_login"], ["Client_password"], client["Client_clientid"], client["Organization"], apikey, ws) # экземпляр класса client_client
                    self.authorized_clients.append(client_client) # добавление клиента в массив авторизированных клиентов
                    await client_client.ws.send((json.dumps({"action": "Login", "status": "true", "data": {"apikey": apikey}}))) # отпркавка сообщения об успешной авторизации клиенту и посыл apikey
                    print("CLIENT AUTHORIZED")
                    break
        else: # если флаг сработал - отправка сообщения клиенту об уже имеющейся авторизации
            await ws.send((json.dumps({"action": "login", "status": "false", "data": "You are already authorized"})))

if __name__ == '__main__':
    port = 9000 # порт сервера
    server = Server() # экземпляр класса Server
    start_server = websockets.serve(server.server_handler, "127.0.0.1", port, ping_interval=None) # запуск сервера
    print("SERVER STARTED on port : " + str(port))
    loop = asyncio.get_event_loop() # асинхронная петля
    loop.run_until_complete(start_server) # запуск петли и функции обработки сервера
    loop.run_forever() # параметр петли: запускать всегда