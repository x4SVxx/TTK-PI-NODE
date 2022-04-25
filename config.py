

class Config():

    def __init__(self):

        # list of anchors
        self.anchors = []
        # list of tags
        self.tags = []
        # dw tic, sec (~16 ps)
        self.dw_unit = (1.0 / 499.2e6 / 128.0)
        # timer overflow, sec
        self.T_max = pow(2., 40.) * self.dw_unit
        # height of tags
        self.hei = []
        # speedoflight
        self.c = 299792458.
        # max zone
        self.zone = 1000.
        # stream
        self.stream = []
        # log enable
        self.log = 0
        self.logger = []

        # accumulation params
        self.accumulation_mode = 0
        self.buffer_length = 10