"""
    Alberto da Silva - 10 April 2022
    junteks / juntek / junce
    http://www.junteks.com/product/278218225
    KG140F coulometer meter that uses a SHUNT to
        Measure voltage (V),    10-120V, with 0.01V resolution
                current (A),     0-400A, with 0.1A  resolution
                power (W) (V*A), 0-180kW with 0.01W resolution
                charge (Ah),     0.001Ah resolution
                discharge (Ah),  0.001Ah resolution
                watt-hours (Wh),
                time (S)
                Temperature (C) via external probe with 1C resolution
        Has a display
        Has a RS485 serial interface
        The sensor values are publised (unsolicied) to the serial interface
        See KG140F manual for message format

    Manual: http://68.168.132.244/KG-F_EN_manual.pdf

    https://www.lithium-battery-factory.com/lithium-battery-state-of-charge/
    To correct drift, the coulomb counter should be recalibrated (reset) at each load cycle.
"""

import time
import logging

# utility functions/classes
from .movingavg import MovingAvg
from .iround import iround

logger = logging.getLogger(__name__)

# See "4.Introduction of the display interface", KG-F_EN_manual.pdf page 10  # (number)
# cumulative_Ah * voltage = Wh
#   increases with charge & discharge 
#      use 'direction' to compute energy_in/out
JUNTEK_R50_DICT = {
   'current':                    {'idx':2,  'unit':'A',   'factor':'f100'},  # 16
   'voltage':                    {'idx':3,  'unit':'V',   'factor':'f100'},  # 15
   'capacity_Ah':                {'idx':4,  'unit':'Ah',  'factor':'f1000'}, # 14
   'cumulative_Ah':              {'idx':5,  'unit':'Ah',  'factor':'f1000'}, # 13 Reset via W62 at 100%SoC -> discharge_Ah
   'charge_Wh':                  {'idx':6,  'unit':'Wh',  'factor':'f100'},  # 8  Reset via W62 at 100%SoC -> charge_Wh
   'run_time_record':            {'idx':7,  'unit':'int', 'factor':'int'},   # 5  Reset via W10 at 100%SoC
   'temperature':                {'idx':8,  'unit':'°C',  'factor':'f-100'}, # 4
#  'unknown_9':                  {'idx':9,  'unit':'null','factor':'int'},
   'relay_state':                {'idx':10, 'unit':'int', 'factor':'int'},   # 2
   'direction':                  {'idx':11, 'unit':'int', 'factor':'int'},   # 9
   'battery_time_left':          {'idx':12, 'unit':'mn',  'factor':'int'},   # 12 Reset via W62 at 100%SoC -> discharge minutes
   'battery_internal_resistance':{'idx':13, 'unit':'mO',  'factor':'f100'},  # 11
   'power':                      {'idx':100,'unit':'W',   'factor':'f10'},   # 100 A*V
   'power_in':                   {'idx':101,'unit':'W',   'factor':'f10'},   # 101 A*V
   'power_out':                  {'idx':102,'unit':'W',   'factor':'f10'},   # 102 A*V
   'SoC':                        {'idx':103,'unit':'%',   'factor':'f10'},   # 103
   'preset_battery_capacity_Ah': {'idx':104,'unit':'Ah',  'factor':'f10'},   # 104
   'energy_in':                  {'idx':105,'unit':'Wh',  'factor':'f1000'}, # 105
   'energy_out':                 {'idx':106,'unit':'Wh',  'factor':'f1000'},  # 106
   'energy_today_in':            {'idx':107,'unit':'Wh',  'factor':'f1000'},  # 107
   'energy_today_out':           {'idx':108,'unit':'Wh',  'factor':'f1000'},  # 108
#  'message_count':              {'idx':109,'unit':'int', 'factor':'int'},   # 108
   'time':                       {'idx':110,'unit':'tm',  'factor':'tm'},    # 110
}

# Limits to check before clear accumulated data
#  - cumulative_Ah, charge_Wh, run_time_record
# These limits are for Hubble Lithium AM2
LIMIT_VOLT = 53.4
LIMIT_SOC = 99.9

def calculate_checksum(line_list: list) -> int:
    """
    From the manual: (4) Checksum:
               check sum is obtained by adding 1 to the remainder of 255 after the sum of all the numbers after the check sum.
    If the sum of the check is taken as 0, it means that it is not verified.
    Example: b':r00=1,217,2140,110,6,\r\n'
             217 = given_sum
             2140 + 110 + 6 (payload) = 2256 % 255 = 216 + 1 = 217
    if error: return negative
    else: return check_sum
    """
    # need a minimum of 4 fields r00=1,sum,data,\n\r and all isdigit
    if len(line_list) < 4 or not all(idx.isdigit() for idx in line_list[1:-1]):
        return -1

    given_sum=int(line_list[1])
    if given_sum == 0: # not verified
        return 0

    # sum payload % 255 + 1
    # check_sum = sum([int(idx) for idx in line_list[2:-1]]) % 255 + 1

    check_sum: int = 0
    for idx in line_list[2:-1]:
        check_sum += int(idx)
    check_sum = check_sum % 255 + 1

    if check_sum == given_sum:
        return check_sum
    return -check_sum



def scale_sensor(factor: str, sensor: str):
    """return factor(sensor)"""
    if factor in ('uint', 'null', 'int'):
        return int(sensor) 
    if factor == "f100":
        return round(float(sensor)/100.0, 2) # divide / 100
    if factor == "f1000":
        return round(float(sensor)/1000.0, 3) # divide / 1000
    if factor == 'f-100':
        return round(int(sensor) - 100, 0) #
    return int(sensor)

def iround_sensor(factor: str, sensor: float):
    """return factor(sensor)"""
    if sensor is None:
        return sensor
    if factor in ('int', 'uint'):
        return iround(sensor, 0)
    if factor == 'f-100':
        return iround(sensor, 1)
    if factor == "f10":
        return iround(sensor, 1)
    if factor == "f100":
        return iround(sensor, 2)
    if factor == "f1000":
        return iround(sensor, 3)
    return iround(sensor, 3)


def send_expect(device, send: bytearray, expect: bytearray, retry=3):
    """send message and wait for reply"""
    # clear buffer
    device.reset_input_buffer()
    device.readline()

    # send/expect loop
    for count in range(retry):
        logger.debug("send=%d, message=%s", count, send)
        device.write(send)
        for _ in range(retry):
            line = device.readline()
            if line[:len(expect)] == expect:
                logger.debug("receive=%s",line)
                return
    logger.debug("NOT FOUND=%s",expect)


def set_battery_percent(device, percent: int):
    """ set percentage of battery remaining / AH.Remaining 4:capacity_Ah
        Does not have to be set as it will auto-set to juntek_setting['preset_battery_capacity_Ah']
        TEST: is it percent or Ah?
    """
    logger.debug("set_battery_percent")
    send_expect(device,b':W60=1,51,' + str(percent).encode() + b',\r\n',b':w60=') # Set battery percentage


def set_battery_capacity_ah(device, amp_hour: float):
    """ sets juntek_setting['preset_battery_capacity_Ah'] """
    logger.debug("set_battery_capacity_ah")
    send_expect(device,b':W28=1,216,' + str(int(amp_hour * 10)).encode() + b',\r\n',b':w60=') # Set battery capacity


def set_zero_current(device):
    """ Current clear to zero """
    logger.debug("set_zero_current")
    send_expect(device,b':W61=1,2,1,\r\n',b':w61=') # Zero current


def set_recording(device, state: bool):
    """ Toggle self.juntek_sensor['run_time_record'] """
    logger.debug("set_recording %s",state)
    if state:
        send_expect(device,b':W10=1,2,1,\r\n',b':w10=') # Device Recording ON
    else:
        send_expect(device,b':W10=1,0,0,\r\n',b':w10=') # Device Recording OFF


def set_clear_accumulated_data(device):
    """ Clear accumulated data
            cumulative_Ah = 0
            charge_Wh = 0
            run_time_record = 0
    """
    logger.debug("set_clear_accumulated_data")
    send_expect(device,b':W62=1,2,1,\r\n',b':w62=')


class JuntekKG:
    """ Class to decode Juntek KG serial data """

    # pylint: disable=too-many-instance-attributes
    # Nine is reasonable in this case.
    def __init__(self, device):
        self.juntek_setting = {} # dict()
        self.juntek_sensor = {} # dict()
        self.juntek_sensor_av = {} # dict()
        self.r00_message_count = 0
        self.r50_message_count = 0
        self.r50_message_count_batch = 0
        self.r51_message_count = 0
        self.soc_at_100_count = 0
        self.prev_cumulative_Ah = 0 
        self.device = device


    def get_settings(self):
        """ return settings dict """
        return self.juntek_setting

    def calculate_enegry(self):
        now = time.time()
        seconds = time.time() - self.start_time
        self.start_time = now
        rate = seconds / 3600.0 / 1000.0
        # Battery at 100%, we reset battery energy (kWh)
        SoC = self.juntek_setting['SoC']
        if SoC >= LIMIT_SOC:
            self.juntek_sensor['energy_in'] = 0
            self.juntek_sensor['energy_out'] = 0

        # calc battery in/out kWh
        self.juntek_sensor['energy_in'] = self.juntek_sensor_av['power_in'] * rate
        self.juntek_sensor['energy_out'] = self.juntek_sensor_av['power_out'] * rate

        return
        

    def get_sensors(self):
        """ return moving average of sensors
            sets count_batch = 0 which on next decode_line resets the average
        """
        result = {}
        for name, mv_avg in self.juntek_sensor_av.items():
            factor = JUNTEK_R50_DICT[name]['factor']
            result[name] = iround_sensor(factor, mv_avg.avg())

        result.update(self.calculate_energy())

        #result['SoC']=int(round(result['SoC'],0))
        result['time'] = time.strftime('%FT%T%z')
        self.r50_message_count_batch = 0
        return result


    def zero_sensor_av(self):
        """ zeros the sensor moving average """
        for name in self.juntek_sensor:
            self.juntek_sensor_av[name] = MovingAvg()


    def decode_r50_sensor(self, line_list: list):
        """ Decode r50 sensor messages
            See 2. R instructions - KG-F_EN_manual.pdf pages 25-27
            This is the most common message ~1 per second
        """
        # We need one r51 configuration message before we can decode r50
        if self.r51_message_count < 1:
            return

        self.r50_message_count += 1
        self.r50_message_count_batch += 1

        # decode real sensors
        for name, value in JUNTEK_R50_DICT.items():
            idx = value['idx']
            if idx < 100:
                factor = value['factor']
                self.juntek_sensor[name] = scale_sensor(factor, line_list[idx])

        # On first message, initialise moving columb counter
        if self.r50_message_count == 1:
            self.prev_cumulative_Ah = self.juntek_sensor['cumulative_Ah']
            self.juntek_sensor['energy_in'] = 0
            self.juntek_sensor['energy_out'] = 0
            self.juntek_sensor['energy_today_in'] = 0
            self.juntek_sensor['energy_today_out'] = 0

        energy_delta = (self.juntek_sensor['cumulative_Ah'] - self.prev_cumulative_Ah) * self.juntek_sensor['voltage']

        # computed sensors
        if self.juntek_sensor['direction'] == 0:
            # Discharge
            self.juntek_sensor['current']   = -self.juntek_sensor['current']
            self.juntek_sensor['power_out'] = round(self.juntek_sensor['current'] * self.juntek_sensor['voltage'],3) # 102
            self.juntek_sensor['power_in']  = 0
            self.juntek_sensor['energy_out'] -= energy_delta
            self.juntek_sensor['energy_today_out'] -= energy_delta
        if self.juntek_sensor['direction'] == 1:
            # Charge
            self.juntek_sensor['power_out'] = 0
            self.juntek_sensor['power_in']  = round(self.juntek_sensor['current'] * self.juntek_sensor['voltage'],3) # 101
            self.juntek_sensor['energy_in'] += energy_delta
            self.juntek_sensor['energy_today_in'] += energy_delta

        self.juntek_sensor['power'] = round(self.juntek_sensor['current'] * self.juntek_sensor['voltage'],3) # 100
        self.juntek_sensor['preset_battery_capacity_Ah'] = self.juntek_setting['preset_battery_capacity_Ah']
        self.juntek_sensor['SoC'] = round(100 * self.juntek_sensor['capacity_Ah'] / self.juntek_sensor['preset_battery_capacity_Ah'],1) # (10) SoC

        # On first message, initialise moving average
        if self.r50_message_count_batch == 1:
            self.zero_sensor_av()

        # accumulate the average
        for name, value in self.juntek_sensor.items():
            self.juntek_sensor_av[name].next(value)


    def decode_r00_model(self, line_list: list):
        """ Decode r00 model messages
            See See 2. R instructions - KG-F_EN_manual.pdf pages 25-27
            r00 messages occurr ~1 per 10 seconds
        """
        #logger.debug("r00_line_list=%s",line_list)

        self.r00_message_count += 1

        self.juntek_setting['address'] = line_list[0].replace(":r00=","").replace(".","")

        self.juntek_setting['model'] = "KG" + line_list[2][1:] + "F"
        self.juntek_setting['sensor'] = "UNK"
        if line_list[2][0] == "1":
            self.juntek_setting['sensor'] = "HALL"
        if line_list[2][0] == "2":
            self.juntek_setting['sensor'] = "SHUNT"
        self.juntek_setting['max_voltage']   = int(line_list[1][1])  * 100
        self.juntek_setting['max_current']   = int(line_list[2][2:]) * 10
        self.juntek_setting['version']       = line_list[3]
        self.juntek_setting['serial_number'] = line_list[4]


    def decode_r51_configuration(self, line_list: list):
        """ Decode r051 configuration messages
            r51 messages occurr ~1 per 10 seconds
        """
        #logger.debug("r51_line_list=%s",line_list)
        self.r51_message_count += 1

        self.juntek_setting['over_voltage_protection_V']          = float(line_list[2]) / 100
        self.juntek_setting['under_voltage_protection_V']         = float(line_list[3]) / 100
        self.juntek_setting['positive_over_current_protection_A'] = float(line_list[4]) / 100
        self.juntek_setting['negative_over_current_protection_A'] = float(line_list[5]) / 100
        self.juntek_setting['over_power_protection_W']            = float(line_list[6]) / 100
        self.juntek_setting['over_temperature_protection_C']      = float(line_list[7]) - 100
        self.juntek_setting['protection_recovery_time_S']         = int(line_list[8])
        self.juntek_setting['delay_time_S']                       = int(line_list[9])
        self.juntek_setting['preset_battery_capacity_Ah']         = float(line_list[10]) / 10
        self.juntek_setting['voltage_calibration']                = float(line_list[11]) - 100
        self.juntek_setting['current_calibration']                = float(line_list[12]) - 100
        self.juntek_setting['temperature_calibration']            = float(line_list[13]) - 100
        #self.juntek_setting['Reserved_setting_1']                = int(line_list[14])
        self.juntek_setting['relay_type']                         = int(line_list[15])
        #self.juntek_setting['current_ratio']                      = int("-1")
        self.juntek_setting['voltage_curve_scale']                = int(line_list[16])

        self.juntek_sensor['preset_battery_capacity_Ah'] = self.juntek_setting['preset_battery_capacity_Ah']


    def decode_line(self, line: str):
        """ Process the line read from the serial port
            messages have 4 formats
            :Rxx/:rxx = read send/return
            :Wxx/:wxx = write send/return
        """
        logger.debug("line=%s",line)

        cmd=line[:5] # first five contains the cmd

        # we only process ":rxx" read return messages
        if cmd[:2] != b':r':
            return

        line_list = line.decode().split(",")

        checksum = calculate_checksum(line_list)
        if checksum < 0:
            logger.warning("checksum failed: line=%s, checksum=%d", line, checksum)
            return

        if cmd == b':r50=':
            self.decode_r50_sensor(line_list)
            return

        if cmd == b':r51=':
            self.decode_r51_configuration(line_list)
            return

        if cmd == b':r00=':
            self.decode_r00_model(line_list)
            return


    def run_maintenance(self):
        """ maintenance proc should be run every minute to check if accumulated data needs resetting
            check if voltage > LIMIT_VOLT AND # float voltage]
                     SoC     > LIMIT_SOC  AND # battery fully charged
                     current 0..20        AND # minimal charging
                     checked > 3              # for 3 minutes
                         clear accumulated data in the device
        """
        if self.juntek_sensor["voltage"] >= LIMIT_VOLT and self.juntek_sensor['SoC'] >= LIMIT_SOC and (0 <= self.juntek_sensor['curent'] <= 20):
            self.soc_at_100_count += 1
            logger.info("JUNTEK SOC HAS REACHED %f%%, soc_at_100_count=%d, Volts=%f>=%f AND Amps=%f in 0..20, capacity_Ah=%f, SoC=%f>=%f",
                        self.juntek_sensor['SoC'], self.soc_at_100_count, self.juntek_sensor['voltage'], LIMIT_VOLT,
                        self.juntek_sensor['current'], self.juntek_sensor['capacity_Ah'], self.juntek_sensor['SoC'], LIMIT_SOC)
            if self.soc_at_100_count > 3:
                set_clear_accumulated_data(self.device)
                set_recording(self.device,True)
                self.soc_at_100_count = 0
                self.prev_cumulative_Ah = 0
                self.juntek_sensor['energy_today_in'] = 0
                self.juntek_sensor['energy_today_out'] = 0
        else:
            self.soc_at_100_count = 0


def main():
    print("Juntek KG-F columb meter decoder - Alberto 2022")

if __name__ == '__main__':
    main()
