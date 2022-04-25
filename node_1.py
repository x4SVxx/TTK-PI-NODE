import websockets
import asyncio
import json
from anchor import Anchor
from config import Config
from aioconsole import ainput


class Node:

    def __init__(self):
        self.login = "Node_1"
        self.password = "0001"
        self.server_ip = "127.0.0.1"
        self.server_port = "8088"
        self.apikey = ""
        self.command = ""
        self.buffer = []
        self.anchors = []
        self.anchors_tasks = []

    async def node_handler(self):
        url = f"ws://{self.server_ip}:{self.server_port}"
        async with websockets.connect(url, ping_interval=None) as ws:
            print("NODE STARTED")
            await asyncio.gather(self.node_command_hadler(ws), self.node_receive(ws))

    async def node_command_hadler(self, ws):
        while True:
            self.command = await ainput()

            if self.command == "authorization":
                await ws.send(json.dumps({"action": "authorization", "login": self.login, "password": self.password}))

            if self.command == "getconfig":
                await ws.send(json.dumps({"action": "getconfig", "apikey": self.apikey}))

    async def produce(self, ws):
        await ws.send(json.dumps({"action": "anchor", "number": self.buffer.pop(0)}))

    async def node_receive(self, ws):
        while True:
            message = json.loads(await ws.recv())
            print("MESSAGE from SERVER " + str(message))

            if message["action"] == "warning":
                print(message["warning"])

            if message["action"] == "apikey":
                self.apikey = message["apikey"]
                print("APIKEY: " + self.apikey)

            if message["action"] == "setconfig":
                for number, config in json.loads(message["data"]).items():
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
                        anchor_config = Config()
                        self.anchors_tasks.append(anchor.anchor_handler(self.buffer, anchor_config))

            if message["action"] == "start":
                await asyncio.gather(*self.anchors_tasks)

            if message["action"] == "stop":
                for anchor in self.anchors:
                    anchor.stop()
                print("STOP")


if __name__ == '__main__':
    node = Node()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(node.node_handler())
