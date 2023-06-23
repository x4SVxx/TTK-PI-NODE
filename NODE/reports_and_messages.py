byteorder_def = 'little'

def build_RTLS_CMD_SET_CFG_CCP(M, CP, PRF, DR, PC, PL, PSN_L, PSN_U, ADRx, ADTx, LD, Lag):
    RTLS_CMD_SET_CFG_CCP_VALUE = 0x44
    mes = RTLS_CMD_SET_CFG_CCP_VALUE.to_bytes(1, byteorder=byteorder_def, signed=False)
    val = 0
    mes += val.to_bytes(1, byteorder=byteorder_def, signed=False)
    mes += M.to_bytes(1, byteorder=byteorder_def, signed=False)
    val = CP + PRF * pow(2, 4)
    mes += val.to_bytes(1, byteorder=byteorder_def, signed=False)
    mes += DR.to_bytes(1, byteorder=byteorder_def, signed=False)
    mes += PC.to_bytes(1, byteorder=byteorder_def, signed=False)
    mes += PL.to_bytes(1, byteorder=byteorder_def, signed=False)
    val = PSN_L + PSN_U * pow(2, 4)
    mes += val.to_bytes(1, byteorder=byteorder_def, signed=False)
    mes += ADRx.to_bytes(2, byteorder=byteorder_def, signed=False)
    mes += ADTx.to_bytes(2, byteorder=byteorder_def, signed=False)
    val = 0
    mes += val.to_bytes(1, byteorder=byteorder_def, signed=False)
    mes += LD.to_bytes(1, byteorder=byteorder_def, signed=False)
    val = 0
    mes += val.to_bytes(8, byteorder=byteorder_def, signed=False)
    mes += Lag.to_bytes(4, byteorder=byteorder_def, signed=False)
    return mes

def build_RTLS_START_REQ(ON_OFF):
    RTLS_START_REQ_VALUE = 0x57
    mes = RTLS_START_REQ_VALUE.to_bytes(1, byteorder=byteorder_def, signed=False)
    mes += ON_OFF.to_bytes(1, byteorder=byteorder_def, signed=False)
    return mes

def decode_anchor_message(data):
    FnCE = data[0]
    msg = {}
    if FnCE == 49:  # 0x31
        msg["type"] = "CS_RX"
        msg["sender"] = data[2:10]
        msg["receiver"] = []
        msg["seq"] = data[1]
        msg["timestamp"] = int.from_bytes(data[10:15], byteorder=byteorder_def, signed=False) * (1.0 / 499.2e6 / 128.0)
    elif FnCE == 50:  # 0x32 COMPATIBLE
        msg["type"] = "BLINK"
        msg["sender"] = data[2:10]
        msg["receiver"] = []
        msg["sn"] = data[1]
        msg["state"] = []
        msg["timestamp"] = int.from_bytes(data[10:15], byteorder=byteorder_def, signed=False) * (1.0 / 499.2e6 / 128.0)
        msg["tx_timestamp"] = []
    elif FnCE == 48:  # 0x30
        msg["type"] = "CS_TX"
        msg["sender"] = []
        msg["receiver"] = []
        msg["seq"] = data[1]
        msg["timestamp"] = int.from_bytes(data[2:7], byteorder=byteorder_def, signed=False) * (1.0 / 499.2e6 / 128.0)
    elif FnCE == 52:  # 0x34 TX_TS
        msg["type"] = "BLINK"
        msg["sender"] = data[2:10]
        msg["receiver"] = []
        msg["sn"] = data[1]
        msg["state"] = data[20]
        msg["timestamp"] = int.from_bytes(data[10:15], byteorder=byteorder_def, signed=False) * (1.0 / 499.2e6 / 128.0)
        msg["tx_timestamp"] = int.from_bytes(data[15:20], byteorder=byteorder_def, signed=False) * (1.0 / 499.2e6 / 128.0)
    elif FnCE == 53:  # 0x35 SHORT
        msg["type"] = "BLINK"
        msg["sender"] = data[2:10]
        msg["receiver"] = []
        msg["sn"] = data[1]
        msg["state"] = data[15]
        msg["timestamp"] = int.from_bytes(data[10:15], byteorder=byteorder_def, signed=False) * (1.0 / 499.2e6 / 128.0)
        msg["tx_timestamp"] = []
    elif FnCE == 66:  # 0x42
        msg["type"] = "Config request"
        msg["receiver"] = data[1:9]
    else:
        msg["type"] = "Unknown"
    return msg