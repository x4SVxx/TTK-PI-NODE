import datetime
import socket
import json
# from influxdb import InfluxDBClient

class Config():

    def __init__(self):

        self.isworking = 1

        # COORDINATES CALCULATING PARAMS

        # list of anchors // first anchor is always master-anchor
        self.anchors = []
        # list of tags
        self.tags = []
        # dw tic, sec (~16 ps)
        self.dw_unit = (1.0 / 499.2e6 / 128.0)
        # timer overflow, sec
        self.T_max = pow(2., 40.) * self.dw_unit
        # current seq number
        self.cur_seq = 1000
        # speedoflight
        self.c = 299792458.
        # max zone
        self.zone = 1000.
        # log-file of all tags
        filename = "logs/" + str(datetime.datetime.now()) + "_" + "ALL.txt"
        filename = filename.replace(" ", "_")
        filename = filename.replace(":", "_")
        filename = filename.replace("-", "_")
        self.filename = filename
        measname = "log" + str(datetime.datetime.now())
        measname = measname.replace(" ", "")
        measname = measname.replace(":", "")
        measname = measname.replace("-", "")
        measname = measname.replace(".", "")
        self.meas_name = measname[:-3]
        self.server_ip = "192.168.99.13"
        self.server_port = 3000

        # self.db_client = InfluxDBClient(host='localhost', port=8086)
        # self.matlab_socket = socket.socket()

        # # Anchors configuration
        # with open("config.json", "r") as file:
        #     self.config = (json.loads(file.read()))
        # # print(self.config)

        # rf configuration
        with open("rf_params.json", "r") as file:
            self.rf_params = (json.loads(file.read()))

        # # list of anchors to configure
        # self.anchors_conf = []
        # with open("anchors.json", "r") as file:
        #     for line in file:
        #         self.anchors_conf.append(json.loads(line))

    
