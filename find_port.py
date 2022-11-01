import concurrent.futures
import driver.robot_comm as rc


def test_conn(ip, port):
    s = rc.open_socket(ip, port, .1)  # Init Response Exception if not robot
    hostname = rc.decode_string(rc.read_mem(13000, "R", s, 40))
    s.close()
    return hostname


if __name__ == '__main__':
    ## Start Thread Pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
        future_conn = {executor.submit(test_conn, "127.0.0.1", port): port for port in range(1024, 65535)}
        for future in concurrent.futures.as_completed(future_conn):
            thread = future_conn[future]
            try:
                robot_hostname = future.result()
            except Exception as e:
                # print('%r generated an exception: %s' % (thread, e))
                continue
            else:
                print('%r port is %s' % (thread, robot_hostname))
