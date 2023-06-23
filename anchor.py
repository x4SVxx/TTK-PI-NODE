import socket
import reports_and_messages as rm
import asyncio


class Anchor:
    def __init__(self, message):
        self.IP = message["ip"]
        self.number = message["number"]
        self.x = message["x"]
        self.y = message["y"]
        self.z = message["z"]
        self.ADRx = int(message["adrx"])
        self.ADTx = int(message["adtx"])
        self.Role = 1 if message["role"] == "Master" else 0
        self.master_number = message["masternumber"]
        self.lag = int(message["lag"])

        self.disconnect_flag = False # флаг детектирование отключения маяка от ноды
        self.disconnect_counter = 0 # счетчик попыток принять сообщение от маяка, если привышает заданное число поднимаем флаг об отключении

        self.socket_flag = False # флаг проверки открытия socket-соединения

        self.Connect()

    def Connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.settimeout(1.0) # timeout чтобы долго не ждать ответа от soket
            self.socket.connect((self.IP, 3000))
            self.socket.recv(3)
            data = self.socket.recv(500)
            msg = rm.decode_anchor_message(data)
            self.ID = msg["receiver"]
            self.name = str(hex(self.ID[1])[2:]) + str(hex(self.ID[0])[2:])
            if not self.disconnect_flag:
                print(f"ANCHOR NUMBER {self.number} WITH NAME {self.name} [IP: {self.IP} ] CONNECTED")
            if self.disconnect_flag:
                print(f"ANCHOR NUMBER {self.number} WITH NAME {self.name} [IP: {self.IP} ] RECONNECTED")
            self.socket_flag = True
        except:
            print(f"ANCHOR NUMBER {self.number} [IP: {self.IP} ] NOT CONNECTED")
            self.socket_flag = False

    async def Reconfig(self, message):
        self.IP = message["ip"]
        self.number = message["number"]
        self.x = message["x"]
        self.y = message["y"]
        self.z = message["z"]
        self.ADRx = int(message["adrx"])
        self.ADTx = int(message["adtx"])
        if message["role"] == "Master":
            self.Role = 1
        else:
            self.Role = 0
        self.master_number = message["masternumber"]
        self.lag = int(message["lag"])
        print(f"ANCHOR {self.number} [IP: {self.IP} ] RECONFIGURATED")

    async def SetRfConfig(self, rf_config):
        self.rf_config = rf_config
        PRF = {16: 1,
               64: 2}
        DATARATE = {110: 0,
                    850: 1,
                    6.8: 2}
        PREAMBLE_LEN = {64: int(0x04),
                        128: int(0x14),
                        256: int(0x24),
                        512: int(0x34),
                        1024: int(0x08),
                        1536: int(0x18),
                        2048: int(0x28),
                        4096: int(0x0C)}
        PAC = {8: 0,
               16: 1,
               32: 2,
               64: 3}
        RTLS_CMD_SET_CFG_CCP = rm.build_RTLS_CMD_SET_CFG_CCP(self.Role,
                                                             rf_config["chnum"],
                                                             PRF[rf_config["prf"]],
                                                             DATARATE[rf_config["datarate"]],
                                                             rf_config["preamblecode"],
                                                             PREAMBLE_LEN[rf_config["preamblelen"]],
                                                             PAC[rf_config["pac"]],
                                                             rf_config["nsfd"],
                                                             self.ADRx,
                                                             self.ADTx,
                                                             rf_config["diagnostic"],
                                                             rf_config["lag"])
        try:
            self.socket.sendall(RTLS_CMD_SET_CFG_CCP)
            if not self.disconnect_flag:
                print(f"ANCHOR NUMBER {self.number} WITH NAME {self.name} [IP: {self.IP} ] SET RF CONFIG")
            if self.disconnect_flag:
                print(f"ANCHOR NUMBER {self.number} WITH NAME {self.name} [IP: {self.IP} ] RESET RF CONFIG")
        except:
            print(f"ERROR SET RF_CONFIG ON ANCHOR NUMBER {self.number} WITH NAME {self.name} [IP {self.IP} ]")

    async def StartSpam(self):
        try:
            self.socket.sendall(rm.build_RTLS_START_REQ(1))
            if not self.disconnect_flag:
                print(f"ANCHOR NUMBER {self.number} WITH NAME {self.name} [IP: {self.IP} ] START")
            if self.disconnect_flag:
                print(f"ANCHOR NUMBER {self.number} WITH NAME {self.name} [IP: {self.IP} ] RESTART")
        except:
            print(f"ERROR START SPAM ON ANCOR NUMBER {self.number} WITH NAME {self.name} [IP {self.IP} ]")

    async def Stop(self):
        try:
            self.socket.sendall(rm.build_RTLS_START_REQ(0))
            print(f"ANCHOR NUMBER {self.number} WITH NAME {self.name} [IP: {self.IP} ] STOP")
        except:
            print(f"ERROR STOP ANCHOR NUMBER {self.number} WITH NAME {self.name} [IP {self.IP} ]")

    async def AnchorHandler(self, log_buffer):
        while True:
            if self.disconnect_flag:
                print("TRY RECONNECT ANCHOR")
                self.Connect()
                await self.SetRfConfig(self.rf_config)
                await self.StartSpam()
                self.disconnect_flag = False
            try:
                header = self.socket.recv(3)
                numberofbytes = header[1]
                data = self.socket.recv(numberofbytes)
                self.socket.recv(3)
                message = rm.decode_anchor_message(data)
                message["receiver"] = self.ID
                if message["type"] == "CS_TX":
                    message["sender"] = message["receiver"]
                message["sender"] = str(hex(message["sender"][1])[2:]) + str(hex(message["sender"][0])[2:]) # для корректной отправки данных в формате JSON заменяем байтовое поле с названием маяка на его сокращенное название типа str
                message["receiver"] = str(hex(message["receiver"][1])[2:]) + str(hex(message["receiver"][0])[2:])# для корректной отправки данных в формате JSON заменяем байтовое поле с названием маяка на его сокращенное название типа str
                log_buffer.append(message)
                print(message)
            except:
                print("NOTHING RECIEVE")
                self.disconnect_counter += 1
                if self.disconnect_counter >= 5: # если посылок с маяка нет 50 тиков (10 секунд) поднимаем флаг disconnect
                    self.disconnect_flag = True
                    self.disconnect_counter = 0
            await asyncio.sleep(0.2)
