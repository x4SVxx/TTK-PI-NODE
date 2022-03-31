import asyncio
import websockets
from node_1 import Node

async def main():

    node = Node()
    await node.start_node()

asyncio.run(main())