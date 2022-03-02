import websockets
import asyncio
import random
import json

PORT = 8099

with open('BD.json') as BD:
    BD_DATA = json.load(BD)

authorized_clients = []

async def server(websocket, path):
    print("CLIENT CONNECTED")

    try:
        async for msg in websocket:
            split_msg = msg.split()
            detected_flag = False
            for sections, clients in BD_DATA.items():
                for i in range(len(clients)):
                    if clients[i]['Client_login'] == split_msg[2] and \
                            clients[i]['Client_password'] == split_msg[3]:
                        authorized_clients.append(clients[i]['Client_login'])
                        await websocket.send(str(random.randint(0, 9)))
                        detected_flag = True
            if not detected_flag:
                await websocket.send("EXIT PLEASE")
    except:
        print("CLIENT DISCONNECT")

async def main():
    tasks = []

start_server = websockets.serve(server, "localhost", PORT)
print("SERVER STARTED on port : " + str(PORT))

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()