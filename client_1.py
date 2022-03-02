import websockets
import asyncio

async def client(login: str, password: str, hostname: str, port: int):
    url = f"ws://{hostname}:{port}"

    async with websockets.connect(url) as ws:
        while True:
            await ws.send("HELLO SERVER " + login + " " + password)
            msg = await ws.recv()
            print(msg)



login = "Client_1"
password = "0001"

hostname = "127.0.0.1"
port = 8088

asyncio.get_event_loop().run_until_complete(client(login, password, hostname, port))