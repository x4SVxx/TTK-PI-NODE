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

with open('rf_params.json') as rf_params:
    rf_config = json.load(rf_params)

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
            ID_flag = False
            for node in self.authorized_nodes:
                if split_command[1] == node.roomid:
                    ID_flag = True
                    if split_command[0] == "SetConfig":
                        await node.ws.send((json.dumps({"action": "SetConfig", "apikey": node.apikey, "data_anchors": json.dumps(anchors_config)})))
                    elif split_command[0] == "SetRfConfig":
                        await node.ws.send((json.dumps({"action": "SetRfConfig", "apikey": node.apikey, "data_rf_config": json.dumps(rf_config)})))
                    elif split_command[0] == "start":
                        await node.ws.send((json.dumps({"action": "Start", "apikey": node.apikey,})))
                    elif split_command[0] =="stop":
                        await node.ws.send((json.dumps({"action": "Stop", "apikey": node.apikey,})))
                    else:
                        print("UNKNOWN COMMAND")
                    break
            if not ID_flag:
                print("UNKNOWN NODE ID")

    async def server_receive(self, ws):
        while True:
            message = json.loads(await ws.recv())
            authorization_flag = False
            node_ID = ""
            for node in self.authorized_nodes:
                if ws == node.ws:
                    authorization_flag = True
                    node_ID = node.roomid
            if not authorization_flag:
                print("MESSAGE from unknown node: " + str(message))
            else:
                print("MESSAGE from node " + node_ID + " " + str(message))

            if message["action"] == "Login":
                authorization_flag = False
                for node in self.authorized_nodes:
                    if ws == node.ws:
                        authorization_flag = True
                if not authorization_flag:
                    await self.authorization(message, ws)
                else:
                    await ws.send((json.dumps({"action": "warning", "warning": "You are already authorized"})))

    async  def authorization(self, message, ws):
        for number, node in BD_DATA.items():
            if node["Node_login"] == message["login"] and \
                    node["Node_password"] == message["password"] and\
                    node["Node_roomid"] == message["roomid"]:
                apikey = generate_apikey()
                client_node = Client_node(message["roomid"], message["login"], message["password"], apikey, ws, node["Node_clientid"], node["Node_roomname"])
                self.authorized_nodes.append(client_node)
                await client_node.ws.send((json.dumps({"action": "Login", "status": "true", "data": {"apikey": apikey, "clientid": node["Node_clientid"], "roomname": node["Node_roomname"]}})))
                print(str(node["Node_roomid"]) + " AUTHORIZED")
                break


if __name__ == '__main__':
    port = 8088
    server = Server()
    start_server = websockets.serve(server.server_handler, "localhost", port, ping_interval=None)
    print("SERVER STARTED on port : " + str(port))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.run_forever()