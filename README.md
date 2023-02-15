# Junteks / Juntek / Junce KG-F / KG140F high precision couloumb meter reader

Python 3 module that reads & decodes Juntek KG-F coulomb meter sensors via RS485 serial interface.

The KG-F uses an inline SHUNT to measure DC voltage and current.  Sensor data is output on the RS485 interface. This module decodes the data. Once decoded the sensor data can be used to supplement IoT information in a Solar PV + Inverter + Battery system.

![Juntek KG140F](/images/Juntek-KG140F.png)

See [Juntek Website](http://www.junteks.com/product/278218225/) website for more information on KG-F series meters.

> ⚠️ DISCLAIMER: Use at your own risk!

## 📖 Manual

Please see [KG-F_EN_manual.pdf](/manual/KG-F_EN_manual.pdf) for message format

## 💎 KG-F Technical specifications

KG-F series is high precision coloumb meter with a SHUNT that has sensors to monitor:

| Sensor          | Unit | Range      | Resolution | Notes                     |
| --------------- | ---- | ---------- | ---------- | ------------------------- |
| Voltage         | V    | 10-120V DC | 0.01V      | via terminals             |
| Current         | A    | 0-400A     | 0.1A       | via Shunt                 |
| Power (V*A)     | W    | 0-180kW    | 0.01W      | computed                  |
| Capacity        | Ah   |            | 0.001Ah    | How full is the battery   |
| Preset Capacity | Ah   |            |            | Size of your battery      |
| Watt-hours      | Wh   | 0.001Wh    |            | Resettable Accumulator    |
| Run Time        | s    | 1-999999s  |            | Run time since reset      |
| Temperature     | °C   | -20-120°C  | 1°C        | Via external probe        |
| Relay State     | bit  | 0-1        | 1          | Relay status              |
| Direction       | bit  | 0-1        | 1          | Direction of current flow |


The KG140F has many other features:
- LCD display
- RS485 serial interface
- Shunt interface to read current
- Voltage interface to read voltage
- Temperature interface
- Relay interface
- Over/Under Voltage Checking which can be used to trigger the relay.

This code is for decoding the sensor data and does not program the relays.

With this Python software and a Juntek KG-F meter you can:  
Access instantaneous:
- current direction
- voltage (V)
- current (A)
- power (W) (V*A)
- battery temperature (°C)

Access cumulative:
- Amp Hours (Ah)
- Watt Hours (Wh)

Development/test environment:
- Juntek KG140F coloumb meter with SHUNT, display and RS485 interface
- Raspberry Pi 3B
- Debian Buster 10
- Python 3.7.3
- Peacefair USB-RS485 adpater

![Peacefair USB-RS485 adpater](/images/Peacefair_USB_RS485_adpater.jpg)

Main use is to act as a decode gateway to mqtt:
- Read & decode sensor data and send to Home Assistant via mqtt
- Produce charts via Grafana

## 📜 AM2 Python Library installation

Clone the repo and pip3 install
```bash
# Install prerequisites
$ pip3 install serial

# Install into .local
$ git clone https://github.com/mysystem32/juntek_kg.git
$ cd juntek_kg
$ pip3 install .
```


## 🔎 Juntek KG Sensor Numbers

The image below has RED numbers that are documented in section **4.Introduction of the display interface** on page 10 of the KG-F manual.

![Juntek KG Sensor Numbers](/images/juntek_sensor_numbers.jpg)

The [BLUE] numbers refer to the sensor key in JUNTEK_R50_DICT dictionary below:

```python
JUNTEK_R50_DICT = {
#key
   2: {'name':'current',                    'unit':'A',   'factor':'f100'},  # 16
   3: {'name':'voltage',                    'unit':'V',   'factor':'f100'},  # 15
   4: {'name':'capacity_Ah',                'unit':'Ah',  'factor':'f1000'}, # 14
   5: {'name':'cumulative_Ah',              'unit':'Ah',  'factor':'f1000'}, # 13 Reset via W62 at 100%SoC -> discharge_Ah
   6: {'name':'charge_Wh',                  'unit':'Wh',  'factor':'f100'},  # 8  Reset via W62 at 100%SoC -> charge_Wh
   7: {'name':'run_time_record',            'unit':'int', 'factor':'int'},   # 5  Reset via W10 at 100%SoC
   8: {'name':'temperature',                'unit':'°C',  'factor':'f-100'}, # 4
   9: {'name':'unknown_9',                  'unit':'null','factor':'int' },
  10: {'name':'relay_state',                'unit':'int', 'factor':'int' },  # 2
  11: {'name':'direction',                  'unit':'int', 'factor':'int' },  # 9
  12: {'name':'battery_time_left',          'unit':'mn',  'factor':'int' },  # 12 Reset via W62 at 100%SoC -> discharge minutes
  13: {'name':'battery_internal_resistance','unit':'mO',  'factor':'f100' }, # 11
 100: {'name':'power',                      'unit':'W',   'factor':'calc' }, # 100 A*V
 101: {'name':'capacity_pct',               'unit':'%',   'factor':'calc' }, # 101
 102: {'name':'preset_battery_capacity_Ah', 'unit':'Ah',  'factor':'calc' }, # 102
 103: {'name':'time',                       'unit':'tm',  'factor':'calc' }, # 103
 104: {'name':'energy_wh',                  'unit':'Wh',  'factor':'calc' }, # 104
 105: {'name':'message_count',              'unit':'int', 'factor':'calc' }  # 105
}
```


## ⚙️ RS485 serial data stream message format

The sensor values are publised (unsolicied) to the serial interface

:R00 Read model - Model, Version, Max Amps, Max Volts, etc
```
b':R00=01.\r\n'
b':r00=1,217,2140,110,6,\r\n'
```
:R51 Read settings - Over/Under voltage/power/temperature/relay state
```
b':R51=01.\r\n'
b':r51=1,12,0,0,0,0,0,100,0,0,4200,100,100,100,0,0,1,\r\n'
```
:R50 Read sensor - current, volts, capacity, direction, temerature, etc
```
b':R50=01.\r\n'
b':r50=1,220,5366,5410,416983,289634,1427701,88851,128,0,0,1,3,4277,\r\n'
```

See section **2. R instructions** on page 25 of the KG-F manual for details on how to decode the R messages


## 🔋 Typical usage

Read voltage, current, temperature, SoC and send data to Home Assistant, etc

see [EXAMPLES.md](/EXAMPLES.md) for sample code.


## ⚖️ License

This project is under the MIT License. See the [LICENSE](LICENSE) file for the full license text.
