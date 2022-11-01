import driver.robot_comm as rc
import driver.srtp_message as sm


if __name__ == '__main__':
    s = rc.open_socket("127.0.0.1", 9022)
    print(sm.DEBUG_HEADER)
    uop6 = rc.read_mem(6006, "I", s)
    print(rc.decode_packet(uop6))
    print(rc.decode_bit(uop6, 6006))
    # print(rc.decode_string(rc.read_mem(13000, "R", s, 40)))
    s.close()

