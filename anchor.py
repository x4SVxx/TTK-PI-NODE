import logging
import socket
import reports_and_messages as rm
import asyncio
import time
import json


class Anchor:

    def __init__(self, msg):
        self.logger = logging.getLogger()
        print(msg["ip"])
        self.IP = msg["ip"]
        self.number = msg["number"]
        self.x = msg["x"]
        self.y = msg["y"]
        self.z = msg["z"]
        self.ADRx = int(msg["adrx"])
        self.ADTx = int(msg["adtx"])
        if msg["role"] == "Master":
            # self.Role = msg["role"]
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
        self.Role = msg["role"]
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
        self.log_message(f"Anchor {self.number} reset")

    def soft_reset(self):
        if self.Role != "Master":
            self.sync_flag = 0
        self.current_master_seq = -1
        self.current_rx = -1.
        self.current_tx = -1.
        self.rx_last_cs = -1.
        self.tx_last_cs = -1.
        self.tx = []
        self.rx = []
        self.k_skip = 0  # number of skipped rx messages by raim

    def anchor_read(self):
        header = self.socket.recv(3)
        numberofbytes = header[1]
        data = self.socket.recv(numberofbytes)
        ending = self.socket.recv(3)
        return rm.Message(data)

    def relate_to_master(self, cfg):
        for master in cfg.anchors:
            if master.number == self.master_number:
                self.master_ID = master.ID

                self.master = master
                self.master_name = master.name
                self.log_message(f"Anchor {self.number} has been related to {self.master.number}")

        if self.master_ID == [] and self.Role == "Master":
            self.sync_flag = 1
            self.log_message(f"Master anchor {self.number} synchronized")

        if self.master_ID == [] and self.Role != "Master":
            self.log_message(f"Anchor {self.number} has no master")

    def update_rf_config(self, msg):

        if self.Role == "Slave":
            master_flag = 0
        else:
            master_flag = 1

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
        RTLS_CMD_SET_CFG_CCP = rm.build_RTLS_CMD_SET_CFG_CCP(master_flag,
                                                             msg['chnum'],
                                                             PRF[msg['prf']],
                                                             DATARATE[msg['datarate']],
                                                             msg['preamblecode'],
                                                             PREAMBLE_LEN[msg['preamblelen']],
                                                             PAC[msg['pac']],
                                                             msg['nsfd'],
                                                             self.ADRx,
                                                             self.ADTx,
                                                             msg['diagnostic'],
                                                             self.lag)

        if self.Role == "Secondary_master":
            RTLS_CMD_SET_CFG_CCP = RTLS_CMD_SET_CFG_CCP[0:14] + self.master_ID + RTLS_CMD_SET_CFG_CCP[22:]

        self.socket.sendall(RTLS_CMD_SET_CFG_CCP)

    # async def receive_data(self):
    #     pass
    #     # header = self.socket.recv(3)
    #     # try:
    #     #     numberofbytes = header[1]
    #     #     data = self.socket.recv(numberofbytes)
    #     #     ending = self.socket.recv(3)
    #     #     msg = rm.decode_anchor_message(data)
    #     #     msg['receiver'] = self.ID
    #     # except:
    #     #     print(header)
    #     #     msg = {}
    #     #     msg['type'] = 'none'
    #
    #     # await self.buffer.put(msg)
    #     # await self.ws.send(json.dumps({"action":"Log","data":str(msg)}))
    #     # return msg

    async def anchor_handler(self, buffer, config):
        # self.socket.sendall(rm.build_RTLS_START_REQ(1))
        RTLS_CMD_SET_CFG_CCP = rm.build_RTLS_CMD_SET_CFG_CCP(self.Role,
                                                             config.rf_params['ch_num'],
                                                             config.rf_params['prf'],
                                                             config.rf_params['datarate'],
                                                             config.rf_params['preamble_code'],
                                                             config.rf_params['preamble_len'],
                                                             config.rf_params['pac'],
                                                             config.rf_params['nsfd'],
                                                             self.ADRx,
                                                             self.ADTx,
                                                             config.rf_params['diagnostic'],
                                                             config.rf_params['lag'])
        self.socket.sendall(RTLS_CMD_SET_CFG_CCP)
        self.socket.sendall(rm.build_RTLS_START_REQ(1))
        while True:
            await asyncio.sleep(0.5)
            buffer.append(self.number)
            try:
                header = self.socket.recv(3)
                numberofbytes = header[1]
                data = self.socket.recv(numberofbytes)
                # msg = rm.decode_anchor_message(data)
                # msg['receiver'] = self.ID
                print(data)
            except:
                print("NOTHING")
            #
            # await self.buffer.put(msg)
            # await self.ws.send(json.dumps({"action":"Log","data":str(msg)}))
            # task = asyncio.create_task(self.receive_data())
            # await asyncio.gather(task)

            # await asyncio.create_task(self.receive_data())
            # print(self.buffer)
            # await self.node.buffer.put(msg)

    # async def get_mes_from_buffer(self):
    #     mes = await self.buffer.get()
    #     return mes

    # def start(self, config):
    #     await self.anchor_handler()


        # await self.anchor_handler()

    def stop(self):
        self.socket.sendall(rm.build_RTLS_START_REQ(0))
        self.soft_reset()

    # def add_tx(self, msg):
    #     if self.master.sync_flag:
    #         self.current_tx = self.master.correct_timestamp(msg['timestamp'])
    #         if self.current_master_seq == msg['seq']:
    #             self.one_step()
    #         else:
    #             self.current_master_seq = msg['seq']
    #
    #
    # def add_rx(self, msg):
    #     self.current_rx = msg['timestamp']
    #     if self.current_master_seq == msg['seq']:
    #         self.one_step()
    #     else:
    #         self.current_master_seq = msg['seq']
    #
    #
    # def one_step(self):
    #     if self.sync_flag:
    #         dt = self.current_tx - self.tx_last_cs
    #         if dt < 0:
    #             dt = dt + self.T_max
    #         b, X, Dx, nev = cl.CS_filter(self.X, self.Dx, dt, self.current_tx, self.current_rx, self.Range, self.T_max)
    #         if self.cfg.log:
    #             self.log_css(b, X, dt, nev)
    #         if b:
    #             self.k_skip = 0
    #             self.X = X
    #             self.Dx = Dx
    #             self.rx_last_cs = self.current_rx
    #             self.tx_last_cs = self.current_tx
    #         else:
    #             self.k_skip = self.k_skip + 1
    #             if self.k_skip == 5:
    #                 self.sync_flag = 0
    #                 self.k_skip = 0
    #                 self.log_message("Sync lost: " + str(self.number))
    #                 self.data2sendflag = 1
    #     else:
    #         if len(self.tx) == self.startnumber:
    #             del self.tx[0]
    #             del self.rx[0]
    #         self.tx.append(self.current_tx)
    #         self.rx.append(self.current_rx)
    #         if len(self.tx) == self.startnumber:
    #             flag, shift, drift = cl.make_initial(self.tx, self.rx, self.Range, self.T_max)
    #
    #             if flag:
    #                 X = np.array([[shift + drift * self.tx[0]], [drift]])
    #                 Dx = self.Dx
    #                 for i in range(1, self.startnumber):
    #                     dt = self.tx[i] - self.tx[i - 1]
    #                     if dt < 0:
    #                         dt = dt + self.T_max
    #                     b, X, Dx, nev = cl.CS_filter(X, Dx, dt, self.tx[i], self.rx[i], self.Range, self.T_max)
    #                     if self.cfg.log:
    #                         self.log_css(b, X, dt, nev)
    #                 self.X = X
    #                 self.Dx = Dx
    #                 self.rx_last_cs = self.rx[len(self.rx) - 1]
    #                 self.tx_last_cs = self.tx[len(self.tx) - 1]
    #                 self.tx = []
    #                 self.rx = []
    #                 self.sync_flag = 1
    #                 self.log_message("Synchronized: " + str(self.number))
    #                 self.data2sendflag = 1
    #     self.current_master_seq = -1
    #
    #
    # def correct_timestamp(self, t):
    #     dt = t - self.rx_last_cs
    #     if dt < 0:
    #         dt += self.T_max
    #     return float(t - (self.X[0] + self.X[1] * dt))

    # def log_message(self, msg):
    #     print(msg)
    #     try:
    #         self.logger.info(msg)
    #     except:
    #         pass

    # def log_css(self, b, X, dt, nev):
    #     data = str(time.time())
    #     data += "\t" + "CLE: CSS"
    #     data += "\t" + str(int(b))
    #     data += "\t" + str(self.number)
    #     data += "\t" + self.name
    #     data += " " + str(X[0][0])
    #     data += " " + str(X[1][0])
    #     data += " " + str(nev[0][0])
    #     data += " " + str(dt)
    #     try:
    #         self.logger.info(data)
    #     except:
    #         pass











