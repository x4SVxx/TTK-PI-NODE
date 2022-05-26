import socket
import reports_and_messages as rm
import asyncio
import json
import numpy as np


class Anchor:

    def __init__(self, msg):
        print(msg["ip"])
        self.IP = msg["ip"]
        self.number = msg["number"]
        self.x = msg["x"]
        self.y = msg["y"]
        self.z = msg["z"]
        self.ADRx = int(msg["adrx"])
        self.ADTx = int(msg["adtx"])
        if msg["role"] == "Master":
            self.Role = 1
        else:
            self.Role = 0
        self.master_number = msg["masternumber"]
        self.lag = int(msg['lag'])
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.socket.connect((self.IP, 3000))
            self.socket.recv(3)
            data = self.socket.recv(500)
            msg = rm.decode_anchor_message(data)
            print(msg)
            self.ID = msg["receiver"]
            self.name = str(hex(self.ID[1])[2:]) + str(hex(self.ID[0])[2:])
            print(f"Anchor {self.number} {self.name} connected")
        except:
            print(f"Anchor {self.number} not connected")

        self.data2sendflag = 0

        self.master = []
        self.master_ID = []
        self.master_name = []
        self.Range = []
        self.sync_flag = 0
        self.current_master_seq = -1
        self.current_rx = -1.
        self.current_tx = -1.
        self.X = []
        self.Dx = []
        self.rx_last_cs = -1.
        self.tx_last_cs = -1.
        self.startnumber = 5
        self.tx = []
        self.rx = []
        self.k_skip = 0  # number of skipped rx messages by raim

    def hard_reset(self, msg):

        self.number = msg["number"]
        self.x = msg["x"]
        self.y = msg["y"]
        self.z = msg["z"]
        self.ADRx = int(msg["adrx"])
        self.ADTx = int(msg["adtx"])
        if msg["role"] == "Master":
            self.Role = 1
        else:
            self.Role = 0
        self.master_number = msg["masternumber"]

        self.master = []
        self.master_ID = []
        self.master_name = []
        self.Range = []
        self.sync_flag = 0
        self.current_master_seq = -1
        self.current_rx = -1.
        self.current_tx = -1.
        self.X = []
        self.Dx = []
        self.rx_last_cs = -1.
        self.tx_last_cs = -1.
        self.startnumber = 5
        self.tx = []
        self.rx = []
        self.lag = int(msg['lag'])
        self.k_skip = 0  # number of skipped rx messages by raim

    async def set_rf_config(self, rf_config):
        PRF = {
            16: 1,
            64: 2
        }
        DATARATE = {
            110: 0,
            850: 1,
            6.8: 2
        }
        PREAMBLE_LEN = {
            64: int(0x04),
            128: int(0x14),
            256: int(0x24),
            512: int(0x34),
            1024: int(0x08),
            1536: int(0x18),
            2048: int(0x28),
            4096: int(0x0C)
        }
        PAC = {
            8: 0,
            16: 1,
            32: 2,
            64: 3
        }
        RTLS_CMD_SET_CFG_CCP = rm.build_RTLS_CMD_SET_CFG_CCP(self.Role,
                                                             rf_config['ch_num'],
                                                             PRF[rf_config['prf']],
                                                             DATARATE[rf_config['datarate']],
                                                             rf_config['preamble_code'],
                                                             PREAMBLE_LEN[rf_config['preamble_len']],
                                                             PAC[rf_config['pac']],
                                                             rf_config['nsfd'],
                                                             self.ADRx,
                                                             self.ADTx,
                                                             rf_config['diagnostic'],
                                                             rf_config['lag'])
        self.socket.sendall(RTLS_CMD_SET_CFG_CCP)

    async def start_spam(self):
        self.socket.sendall(rm.build_RTLS_START_REQ(1))

    async def anchor_handler(self, buffer):
        while True:
            header = self.socket.recv(3)
            try:
                numberofbytes = header[1]
                data = self.socket.recv(numberofbytes)
                ending = self.socket.recv(3)
                msg = rm.decode_anchor_message(data)
                msg['receiver'] = self.ID
                buffer.append(msg)
                print(msg)
            except:
                print("NOTHING")

            await asyncio.sleep(0.2)

    def soft_reset(self):
        if self.Role != 1:
            self.sync_flag = 0
        self.current_master_seq = -1
        self.current_rx = -1.
        self.current_tx = -1.
        self.X = np.array([[0.0], [0.0]])
        self.Dx = np.array([[2.46e-20, 4.21e-20], [4.21e-20, 1.94e-19]])
        self.rx_last_cs = -1.
        self.tx_last_cs = -1.
        self.tx = []
        self.rx = []
        self.k_skip = 0  # number of skipped rx messages by raim

    async def stop(self):
        self.socket.sendall(rm.build_RTLS_START_REQ(0))
        self.soft_reset()