import socket
import struct

import driver.srtp_message as srtp_message


def open_socket(robot_ip, snpx_port, timeout=5):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((robot_ip, snpx_port))
    s.send(srtp_message.INIT_MSG)
    init_resp = s.recv(1024)
    if init_resp[0] != 1:
        raise Exception("Init Response: ", init_resp[0])
    init_comm = read_mem(0, "R", s)
    if init_comm == 256:
        return s
    else:
        raise Exception("Communication Fault: ", init_comm)


def read_mem(addr, reg, s, size=1):
    msg = srtp_message.BASE_MSG.copy()
    msg[42] = srtp_message.SERVICE_REQUEST_CODE["READ_SYS_MEMORY"]
    msg[43] = srtp_message.MEMORY_TYPE_CODE[reg]
    if addr > 0:    # Init Check, if not the init add data.
        msg[44] = int(int((addr - 1) / 8) & 255).to_bytes(1, byteorder='big')
        if (reg == "AI" or reg == "R") or size > 1:
            msg[44] = int(addr - 1 & 255).to_bytes(1, byteorder='big')
        msg[45] = int(addr - 1 >> 8).to_bytes(1, byteorder='big')
    msg[46] = int(size).to_bytes(1, byteorder='big')
    out_bytes = b''.join(msg)

    s.send(out_bytes)
    r = s.recv(1024)

    if addr == 0:  # Init Comm Check
        return struct.unpack('H', bytearray(r[47:49]))[0]
    # print(decode_packet(out_bytes))
    return r


# Maybe seperate this into num regs, strings, I/O
def write_mem(addr, reg, var, s):
    msg = srtp_message.BASE_MSG.copy()
    if type(var) == int:  # Var length might always be 2
        fill = False
        var_length = int(len(format(int(var & 255), '02X') + format(int(var >> 8), '02X')) / 2)  # Could be simplified
    elif type(var) == float:    # Var length might always be 4
        fill = False
        var_length = int((len(hex(struct.unpack('<I', struct.pack('<f', var))[0]))-2) / 2)
    elif type(var) == bool:
        fill = False
        var_length = 1
    elif len(var) % 2:
        fill = True
        var_length = len(var) + 1
    else:
        fill = False
        var_length = len(var)
    msg[4] = var_length.to_bytes(1, byteorder='big')
    msg[9] = b'\x02'    # Base Message set to Read, x02 is for Write
    msg[17] = b'\x02'   # Base Message set to Read, x02 is for Write
    msg[30] = b'\x09'   # Seq Number - 0x09 for Writing
    msg[31] = b'\x80'   # Message Type - Kepware shows \x80 for writing
    msg[42] = var_length.to_bytes(1, byteorder='big')
    msg[48] = b'\x01'
    msg[49] = b'\x01'
    msg[50] = srtp_message.SERVICE_REQUEST_CODE["WRITE_SYS_MEMORY"]
    msg[51] = srtp_message.MEMORY_TYPE_CODE[reg]
    msg[52] = int(addr - 1 & 255).to_bytes(1, byteorder='big')
    msg[53] = int(addr - 1 >> 8).to_bytes(1, byteorder='big')
    msg[54] = (int(var_length / 2)).to_bytes(1, byteorder='big')
    if type(var) == str:
        for data in var:
            msg.append(data.encode('utf8'))
    elif type(var) == float:
        msg.append(bytearray(struct.pack("f", var)))
    else:
        msg.append(int(var & 255).to_bytes(1, byteorder='big'))
        msg.append(int(var >> 8).to_bytes(1, byteorder='big'))
    if type(var) == bool:
        msg[54] = b'\x01'   # Write Length always 1 for bits
        idx = ((addr - 1) % 8)
        if var:
            result = (idx * "0" + "1" + ((8 - idx) * "0"))[::-1]
        else:
            result = "0"
        msg[56] = (int(result, 2).to_bytes(1, byteorder='big'))
        msg.pop()
    if fill:
        msg.append(b'\x00')

    out_bytes = b''.join(msg)
    # print(decode_packet(out_bytes))
    s.send(out_bytes)
    return s.recv(1024)


# For Decoding Registers (GOs and Numeric Registers)
def decode_register(r):
    return struct.unpack('H', bytearray(r[44:46]))[0]


# Decoding Floats (SNPX Multiply set to 0 not 1)
def decode_float(r):
    return struct.unpack('!f', bytes.fromhex(decode_packet(r[44:48][::-1])))[0]


# For Decoding Words (Program Line: PRG[1] in SNPX, etc.)
def decode_word(r):
    return struct.unpack('H', bytearray(r[56:58]))[0]


# For decoding DOs and DIs
def decode_bit(r, addr):
    return format(int(struct.unpack('H', bytearray(r[44:46]))[0]), '08b')[::-1][(addr - 1) % 8]


def decode_string(r):
    return r[56:].decode().rstrip("\x00")


def decode_packet(msg):
    iter_len = sum(1 for _ in enumerate(msg))
    out = ""
    for idx, i in enumerate(msg):
        if iter_len - idx <= iter_len:
            out += " {:02x}".format(i)
    return out
