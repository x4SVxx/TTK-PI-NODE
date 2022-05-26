import websockets
import asyncio
import json
from anchor import Anchor
from aioconsole import ainput


class Node:

    def __init__(self, login, password, roomid, server_ip, server_port):
        self.login = login
        self.password = password
        self.roomid = roomid
        self.server_ip = server_ip
        self.server_port = server_port
        self.apikey = ""
        self.command = ""
        self.buffer = []
        self.anchors = []
        self.anchors_tasks = []

        self.clientid = ""
        self.roomname = ""

        # self.testmsg = {'type': 'CS_RX', 'sender': b'\xb6\xd1\xd0M\x05 \xa3\r', 'receiver': b'\x04\xd2\xd0M\x05 \xa3\r', 'seq': 3, 'timestamp': 0.6012962916917067}

    async def node_handler(self):
        url = f"ws://{self.server_ip}:{self.server_port}"
        async with websockets.connect(url, ping_interval=None) as ws:
            print("NODE STARTED")
            await ws.send(json.dumps({"action": "Login", "login": self.login, "password": self.password, "roomid": self.roomid}))
            await asyncio.gather(self.node_produce(ws), self.node_receive(ws))

    # async def node_command_hadler(self, ws):
    #     while True:
    #         self.command = await ainput()
    #
    #         if self.command == "Login":
    #             await ws.send(json.dumps({"action": "Login", "login": self.login, "password": self.password, "roomid": self.roomid}))
    #
    #         if self.command == "getconfig":
    #             await ws.send(json.dumps({"action": "getconfig", "apikey": self.apikey}))

    async def node_produce(self, ws):
        while True:
            if self.buffer:
                message = self.buffer.pop(0)
                message['sender'] = str(message['sender'])
                message['receiver'] = str(message['receiver'])
                msg ={}
                msg['action'] = 'log'
                msg['data'] = message
                await ws.send(json.dumps(msg))
                print(len(self.buffer))
            await asyncio.sleep(0.01)


    async def node_receive(self, ws):
        while True:
            message = json.loads(await ws.recv())
            print("MESSAGE from SERVER " + str(message))

            if message["action"] == "warning":
                print(message["warning"])

            elif message["action"] == "Login":
                self.apikey = message["data"]["apikey"]
                print("APIKEY: " + self.apikey)
                self.clientid = message["data"]["clientid"]
                self.roomname = message["data"]["roomname"]

            elif message["action"] == "SetConfig" and message["apikey"] == self.apikey:
                for number, config in json.loads(message["data_anchors"]).items():
                    new_anchor_flag = True
                    for anchor in self.anchors:
                        if anchor.IP == config["ip"]:
                            anchor.hard_reset(config)
                            new_anchor_flag = False
                            break
                    if new_anchor_flag:
                        print("NEW ANCHOR")
                        anchor = Anchor(config)
                        self.anchors.append(anchor)

            elif message["action"] == "SetRfConfig" and message["apikey"] == self.apikey:
                for anchor in self.anchors:
                    await anchor.set_rf_config(json.loads(message["data_rf_config"]))

            elif message["action"] == "Start" and message["apikey"] == self.apikey:
                print("START")
                for anchor in self.anchors:
                    await anchor.start_spam()
                for anchor in self.anchors:
                    self.anchors_tasks.append(asyncio.create_task(anchor.anchor_handler(self.buffer)))

            elif message["action"] == "Stop" and message["apikey"] == self.apikey:
                for anchor in self.anchors:
                    await anchor.stop()
                for task in self.anchors_tasks:
                    task.cancel()
                print("STOP")


if __name__ == '__main__':
    node_login = "TestOrg"
    node_password = "TestOrgPass"
    node_roomid = "1"
    node_server_ip = "127.0.0.1"
    node_server_port = "8088"

    node = Node(node_login, node_password, node_roomid, node_server_ip, node_server_port)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(node.node_handler())
