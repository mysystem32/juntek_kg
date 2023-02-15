import logging
import json
import serial
import juntek_kg
from elapsed import Elapsed

logger = logging.getLogger(__name__)

def run_loop(args_port = "/dev/ttyUSB3", args_baudrate = 115200):
    print("Juntek KG-F coloumb meter decoder")
    
    logging.basicConfig(format="%(asctime)s %(levelname)s [%(filename)s:%(lineno)s %(funcName)s()] %(message)s", level=logging.DEBUG)

    device = serial.Serial( port=args_port, baudrate=args_baudrate ) # timeout(float)

    jkg = juntek_kg.JuntekKG(device)

    loop_count = 0
    elapsed=Elapsed(15)

    # READ LOOOP
    while True:
        loop_count += 1
        line = device.readline()
        jkg.decode_line(line)
        if elapsed.check():
            sensors = jkg.get_sensors()
            print(f"MAIN1: sensors={json.dumps(sensors,indent=4)}")

            settings = jkg.get_settings()
            print(f"MAIN2: settings={json.dumps(settings,indent=4)}")

            # send to mqtt

            jkg.run_maintenance()


run_loop()