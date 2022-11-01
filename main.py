import concurrent.futures
import time
from datetime import datetime
import json

import driver.robot_comm as rc
import send_notification as sn

# Robot name in config needs to match Hostname on robot.
with open("config.json", "r") as f:
    plant_config = json.load(f)


## Requests first active alarm from robot.
# Returns nothing if no alarm is present.
def read_alarm(robot_ip, snpx_port, robot):
    sock = rc.open_socket(robot_ip, snpx_port)
    in_auto = int(rc.decode_bit(rc.read_mem(131, "I", sock), 131))  # DO[131] Auto
    faulted = (rc.decode_bit(rc.read_mem(106, "I", sock), 106))  # DO[106] Fault
    alm_str = rc.decode_string(rc.read_mem(7012, "R", sock, 40))  # Active Alarm
    alm_num = rc.decode_register(rc.read_mem(7002, "R", sock, 2))  # Alarm Number
    alm_sev = rc.decode_register(rc.read_mem(7005, "R", sock, 2))  # Alarm Severity
    alm_year = rc.decode_register(rc.read_mem(7006, "R", sock, 2))
    alm_month = rc.decode_register(rc.read_mem(7007, "R", sock, 2))
    alm_day = rc.decode_register(rc.read_mem(7008, "R", sock, 2))
    alm_hour = rc.decode_register(rc.read_mem(7009, "R", sock, 2))
    alm_min = rc.decode_register(rc.read_mem(7010, "R", sock, 2))
    alm_sec = rc.decode_register(rc.read_mem(7011, "R", sock, 2))
    hostname = rc.decode_string(rc.read_mem(13000, "R", sock, 40))  # Robot Hostname
    sock.close()

    # Needs to match time format in config
    alm_time = f"{alm_year:0>2d}-{alm_month:0>2d}-{alm_day} {alm_hour:0>2d}:{alm_min:0>2d}:{alm_sec:0>2d}"
    if type(plant_config["robots"][robot]["last_updated"]) != datetime:
        last_alarm_date = datetime.strptime(plant_config["robots"][robot]["last_updated"], plant_config["system"]["date_format"])
    else:
        last_alarm_date = plant_config["robots"][robot]["last_updated"]

    # Skip setting new date when robot is not faulted - time will be 0's
    if faulted:
        alm_time = datetime.strptime(alm_time, plant_config["system"]["date_format"])
    time.sleep(plant_config["robots"][robot]["update_rate"])  # Sleep for update rate down in config
    if in_auto:
        if faulted and last_alarm_date < alm_time:
            plant_config["robots"][robot]["last_updated"] = alm_time
            return {
                "alm_str": alm_str,
                "alm_num": alm_num,
                "alm_sev": alm_sev,
                "alm_time": alm_time,
                "hostname": hostname
            }
        elif not faulted:
            pass
        else:
            raise NotImplementedError("No (New) Robot Alarm: " + str(alm_time))
    else:
        raise NotImplementedError("Not in Auto: " + str(alm_time))


def start_threads(config):
    ## Start Thread Pool
    # Thread for each robot in plant config
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(config["robots"])) as executor:
        future_to_alm = {executor.submit(read_alarm,
                                         config["robots"][rb]["ip_address"],
                                         config["robots"][rb]["snpx_port"],
                                         rb): rb for rb in config["robots"]}
        for future in concurrent.futures.as_completed(future_to_alm):
            thread = future_to_alm[future]
            try:
                robot_result = future.result()
            except Exception as e:
                print('%r generated an exception: %s' % (thread, e))
            else:
                if robot_result is not None:
                    ## Send email with alarm.
                    print('%r response is %s' % (thread, robot_result["alm_str"]))
                    sn.send_email(robot_result["hostname"], robot_result["alm_str"], robot_result["alm_time"], plant_config)

        futures_done = len(concurrent.futures.wait(future_to_alm, return_when="ALL_COMPLETED")[0])
        while futures_done != len(config["robots"]):
            time.sleep(.1)
        config = json.dumps(config, indent=4, sort_keys=True, default=str)
        with open("config.json", "w") as c:
            c.write(config)


if __name__ == '__main__':
    while True:
        start_threads(plant_config)
        print("----")
