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
        self.authorized_nodes = set()
        self.command = ""

    async def server_handler(self, ws):
        await asyncio.gather(self.server_command_handler(ws), self.server_receive(ws))

    async def server_command_handler(self, ws):
        while True:
            self.command = self.command = await ainput("COMMAND - ")
            if self.command == "setconfig":
                await ws.send((json.dumps({"action": "setconfig", "data": json.dumps(anchors_config)})))
            elif self.command == "start":
                await ws.send((json.dumps({"action": "start"})))
            elif self.command =="stop":
                await ws.send((json.dumps({"action": "stop"})))
            elif self.command =="gettasks":
                await ws.send((json.dumps({"action": "gettasks"})))

    async def server_receive(self, ws):
        while True:
            message = json.loads(await ws.recv())
            print("MESSAGE " + message)

            if message["action"] == "authorization":
                await self.authorization(message, ws)

    async  def authorization(self, message, ws):
        for i in range(len(BD_DATA["Nodes"])):
            if BD_DATA["Nodes"][i]["Node_login"] == message["login"] and \
                    BD_DATA["Nodes"][i]["Node_password"] == message["password"]:
                apikey = generate_apikey()
                client_node = Client_node(BD_DATA["Nodes"][i]["Node_ID"], message["login"], message["password"], apikey, ws)
                self.authorized_nodes.add(client_node)
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