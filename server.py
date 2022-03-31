import websockets
import asyncio
import json
import string
from client_node import Client_node
from aioconsole import ainput
import secrets


with open('BD.json') as BD:
    BD_DATA = json.load(BD)

with open('anchors.json') as anchors:
    anchors_config = json.load(anchors)

def generate_apikey():
    letters_and_digits = string.ascii_letters + string.digits
    apikey = ''.join(secrets.choice(letters_and_digits) for i in range(30))
    return apikey


class Server:

    def __init__(self):
        self.authorized_nodes = []
        self.command = ""

    async def server_handler(self, ws):
        await asyncio.gather(self.server_command_handler(), self.server_receive(ws))

    async def server_command_handler(self):
        while True:
            self.command = self.command = await ainput()
            split_command = self.command.split()
            ws = None
            ws_flag = False
            for node in self.authorized_nodes:
                if split_command[1] == node.ID:
                    ws = node.ws
                    ws_flag = True
            if ws_flag:
                if split_command[0] == "setconfig":
                    await ws.send((json.dumps({"action": "setconfig", "data": json.dumps(anchors_config)})))
                elif split_command[0] == "start":
                    await ws.send((json.dumps({"action": "start"})))
                elif split_command[0] =="stop":
                    await ws.send((json.dumps({"action": "stop"})))
                elif split_command[0] =="gettasks":
                    await ws.send((json.dumps({"action": "gettasks"})))
            else:
                print("UNKNOWN NODE ID")

    async def server_receive(self, ws):
        while True:
            message = json.loads(await ws.recv())

            authorization_flag = False
            node_ID = ""
            for node in self.authorized_nodes:
                if ws == node.ws:
                    authorization_flag = True
                    node_ID = node.ID
            if not authorization_flag:
                print("MESSAGE from unknown node: " + str(message))
            else:
                print("MESSAGE from node " + node_ID + " " + str(message))

            if message["action"] == "authorization":
                authorization_flag = False
                for node in self.authorized_nodes:
                    if ws == node.ws:
                        authorization_flag = True
                if not authorization_flag:
                    await self.authorization(message, ws)
                else:
                    await ws.send((json.dumps({"action": "warning", "warning": "You are already authorized"})))

    async  def authorization(self, message, ws):
        for i in range(len(BD_DATA["Nodes"])):
            if BD_DATA["Nodes"][i]["Node_login"] == message["login"] and \
                    BD_DATA["Nodes"][i]["Node_password"] == message["password"]:
                apikey = generate_apikey()
                client_node = Client_node(BD_DATA["Nodes"][i]["Node_ID"], message["login"], message["password"], apikey, ws)
                self.authorized_nodes.append(client_node)
                await client_node.ws.send((json.dumps({"action": "apikey", "apikey": apikey})))
                print(str(BD_DATA["Nodes"][i]["Node_ID"]) + " AUTHORIZED")
                break


if __name__ == '__main__':
    port = 8088
    server = Server()
    start_server = websockets.serve(server.server_handler, "localhost", port, ping_interval=None)
    print("SERVER STARTED on port : " + str(port))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.run_forever()