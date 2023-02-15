# Juntek KG example code

The examples folder contains some sample code that display data from the Juntek KG
- Print all sensor data from Juntek KG - [examples/print_all.py](/examples/print_all.py)

## Home Assistant

Integration to HA can be done via mqtt see
[examples/juntek_kg2mqtt.py](/examples/juntek_kg2mqtt.py)  
This is a sample application that 
- reads Juntek KG sensors
- publishes to mqtt

juntek_kg2mqtt.py can publish mqtt HASS compatible discovery messages so that Home Assistant will "auto discover" the Juntek KG

```bash
ads@solar-assistant:~/juntek_kg/examples $ python3 juntek_kg2mqtt.py --help
usage: juntek_kg2mqtt.py [-h] --device DEVICE 
                      [--mqtt] [--mqtt-user MQTT_USER]
                      [--mqtt-password MQTT_PASSWORD]
                      [--mqtt-broker MQTT_BROKER] [--mqtt-port MQTT_PORT]
                      [--mqtt-topic MQTT_TOPIC] [--mqtt-hass]
                      [--mqtt-hass-retain] [--debug] [--sleep SLEEP]

Juntek KG to HASS via MQTT example app

optional arguments:
  -h, --help            show this help message and exit
  --device DEVICE       RS232 device, e.g. /dev/ttyUSB1
  --mqtt                MQTT enable message publish
  --mqtt-user           MQTT username
  --mqtt-password       MQTT password
  --mqtt-broker         MQTT broker (server), default localhost
  --mqtt-port           MQTT port, default 1883
  --mqtt-topic          MQTT topic, default 'hubble_am2'
  --mqtt-hass           MQTT enable Home Assistant discovery
  --mqtt-hass-retain    MQTT enable retain HASS discovery mesages
  --debug               Enable debug output
  --sleep SLEEP         Seconds bettwen sampling loop, default=60
```

![Home Assistant Integration 1](/images/home-assistant-1.png)

The full set of sensors can be accessed
![Home Assistant Integration 2](/images/home-assistant-2.png)

## Grafana dashboards

Once AM data is stored in a database eg PostgreSQL / MySQL / InfluxDB, Grafana dashboards can be built.  

This dashboard below shows the pack cycles increasing with the SoC  
The Cycle count seems to go up about 1.5 times per day
![pack cycles 7 days](/images/pack_cycles_7_days.png)

This dashboard below shows the 13 cells voltage in pack 4.  
Cell 13 seems to be a bit lower that the rest.
![pack4 cell voltages](/images/pack4_cell_voltage.png)
