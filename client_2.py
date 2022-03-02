import websockets
import asyncio

async def client(login, password):
    url = "ws://127.0.0.1:8099"

    async with websockets.connect(url) as ws:
        # await ws.send("HELLO SERVER " + login + " " + password)
        while True:
            await ws.send("HELLO SERVER " + login + " " + password)
            msg = await ws.recv()
            print(msg)

login = "Client_2"
password = "0002"
asyncio.get_event_loop().run_until_complete(client(login, password))