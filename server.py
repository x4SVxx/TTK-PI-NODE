import websockets
import asyncio
import random
import json
from websockets import WebSocketServerProtocol

with open('BD.json') as BD:
    BD_DATA = json.load(BD)

class Server:

    authorized_clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        # self.authorized_clients.add(ws)
        try:
            async for message in ws:
                split_message = message.split()
                for i in range(len(BD_DATA['Clients'])):
                    if BD_DATA['Clients'][i]['Client_login'] == split_message[2] and \
                            BD_DATA['Clients'][i]['Client_password'] == split_message[3]:
                        self.authorized_clients.add(ws)
                        break
        except:
            pass

    async def unregister(self, ws: WebSocketServerProtocol):
        self.authorized_clients.remove(ws)

    async def distribute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            if self.authorized_clients:
                for client in self.authorized_clients:
                    await client.send(str(random.randint(0, 9)))

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distribute(ws)
        except:
            pass
        finally:
            await self.unregister(ws)



port = 8088
server = Server()
start_server = websockets.serve(server.ws_handler, "localhost", port)
print("SERVER STARTED on port : " + str(port))

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()