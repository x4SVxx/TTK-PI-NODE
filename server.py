import websockets
import asyncio
import json
import string
from client_node import Client_node
from aioconsole import ainput
import secrets


"""Загрузка баззы данных нод из JSON файла"""
with open('BD.json') as BD:
    BD_DATA = json.load(BD)

"""Загрузка config из JSON файла"""
with open('anchors.json') as anchors:
    anchors_config = json.load(anchors)

"""Загрузка config другой конфигурации из JSON файла"""
with open('anchors2.json') as anchors2:
    anchors_config2 = json.load(anchors2)

"""Загрузка rf_config из JSON файла"""
with open('rf_params.json') as rf_params:
    rf_config = json.load(rf_params)


"""Функция генерации apikey - ключа безопасности для общения с нодой"""
def generate_apikey():
    letters_and_digits = string.ascii_letters + string.digits
    apikey = ''.join(secrets.choice(letters_and_digits) for i in range(30))
    return apikey


"""Класс сервера"""
class Server:

    def __init__(self):
        self.authorized_nodes = []   # массив с авторизированными нодами
        self.command = ""            # строка с командой из консоли

    """Функция обработки сервера"""
    async def server_handler(self, ws):
        await asyncio.gather(self.server_command_handler(), self.server_receive(ws)) # запуск асинхронной работы приемной и передающей функций сервера

    """Функция обработки консольных команд сервера"""
    async def server_command_handler(self):
        while True: # бесконечный цикл для непрерывной проверки ввода команды
            self.command = self.command = await ainput() # асинхронный ввод команды из консоли
            split_command = self.command.split() # разделение строки введенной команды на слова, первое слово - команда, второе - ID ноды
            ID_flag = False # флаг для проверки есть ли данный ID в уже авторизованных
            for node in self.authorized_nodes: # пробежка по элементам массива уже авторизированных нод
                if split_command[1] == node.roomid: # проверка есть ли введенный ID в авторизированных нодах
                    ID_flag = True # активация флага наличия введенного ID в авторизованных
                    if split_command[0] == "SetConfig": # команада установки config
                        await node.ws.send((json.dumps({"action": "SetConfig", "status": "true", "data": anchors_config}))) # отправка сообщения с config на ноду
                    elif split_command[0] == "SetConfig2": # команада установки config с другой конфигурацией
                        await node.ws.send((json.dumps({"action": "SetConfig", "status": "true", "data": anchors_config2}))) # отправка сообщения с config с другой конфигурацией на ноду
                    elif split_command[0] == "SetRfConfig": # команада установки rf_config
                        await node.ws.send((json.dumps({"action": "SetRfConfig", "status": "true", "data": rf_config}))) # отправка сообщения с rf_config на ноду
                    elif split_command[0] == "Start": # команада старт
                        await node.ws.send((json.dumps({"action": "Start", "status": "true"}))) # отправка сообщения с командо старт на ноду
                    elif split_command[0] =="Stop": # команада стоп
                        await node.ws.send((json.dumps({"action": "Stop", "status": "true"}))) # отправка сообщения с командой стоп на ноду
                    else: # если ни одно условие не выполняется - сообщение о несуществующей команде
                        print("UNKNOWN COMMAND")
                    break
            if not ID_flag: # если флаг не сработал - сообщение о несуществующем ID ноды
                print("UNKNOWN NODE ID")

    """Функция приема сервера"""
    async def server_receive(self, ws):
        while True: # запуск бесконечного цикла для непрерывной работы функции
            message = json.loads(await ws.recv()) # прием сообщения от ноды
            authorization_flag = False # флаг авторизации
            node_ID = "" # ID ноды
            for node in self.authorized_nodes: # пробежка по элементам массива с авторизированными нодами
                if ws == node.ws: # сравнение двух websocket-соединений
                    authorization_flag = True # активация флага авторизации
                    node_ID = node.roomid # присваивание ID ноде
            if not authorization_flag: # если флаг не сработал - сообщение от неизвестной ноды
                print("MESSAGE from unknown node: " + str(message))
            else: # если флаг сработал - сообщение от известной ноды
                print("MESSAGE from node " + node_ID + " " + str(message))

            if message["action"] == "Login": # обтаботка авторизации
                authorization_flag = False # флаг авторизации
                for node in self.authorized_nodes: # пробежка по элементам массива с авторизированными нодами
                    if ws == node.ws: # сравнение двух websocket-соединений
                        authorization_flag = True # активация флага авторизации
                if not authorization_flag: # если флаг не сработал - отправка ноды на авторизацию
                    await self.login(message, ws)
                else: # если флаг сработал - отправка сообщения на ноду об уже имеющейся авторизации
                    await ws.send((json.dumps({"action": "login", "status": "false", "data": "You are already authorized"})))

            elif message["action"] == "Log" and message["status"] == "true": # обработка логирования
                for node in self.authorized_nodes: # пробежка по элементам массива авторизированных нод
                    if node.apikey == message["apikey"]: # сравнение apikey, если имеется схожий - прием логирования
                        # message["data"]["sender"] = message["data"]["sender"].encode("utf-16", "strict")[2:]
                        # message["data"]["receiver"] = message["data"]["receiver"].encode("utf-16", "strict")[2:]
                        print("Log from node " + node.roomid + " " + str(message))

    """Функция авторизации ноды"""
    async  def login(self, message, ws):
        for number, node in BD_DATA.items(): # пробежка по элементам базы данных
            if node["Node_login"] == message["login"] and \
                    node["Node_password"] == message["password"] and\
                    node["Node_roomid"] == message["roomid"]: # сравнение логина, пароля и roomid
                apikey = generate_apikey() # генерация apikey
                client_node = Client_node(message["roomid"], message["login"], message["password"], apikey, ws, node["Node_clientid"], node["Node_roomname"], node["Organization"]) # экземпляр класса client_node
                self.authorized_nodes.append(client_node) # добавление ноды в массив авторизированных
                await client_node.ws.send((json.dumps({"action": "Login", "status": "true", "data": {"apikey": apikey, "clientid": node["Node_clientid"], "roomname": node["Node_roomname"], "name": node["Organization"]}}))) # отпркавка сообщения об успешной авторизации на ноды и посыл apikey
                print("Organization: " + str(node["Organization"]) + " | " + "Node ID: " + str(node["Node_roomid"]) + " | " + "roomname: " + str(node["Node_roomname"]) + " | " + "client_id: " + str(node["Node_clientid"]) + " | " + " AUTHORIZED")
                break


if __name__ == '__main__':
    port = 9000 # порт сервера

    server = Server() # экземпляр класса Server
    start_server = websockets.serve(server.server_handler, "localhost", port, ping_interval=None) # запуск сервера
    print("SERVER STARTED on port : " + str(port))
    loop = asyncio.get_event_loop() # асинхронная петля
    loop.run_until_complete(start_server) # запуск петли и функции обработки ноды
    loop.run_forever() # параметр петли - запускать всегда