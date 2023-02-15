"""
    Description: Junteck to mqtt publish discovery and sensors
    Author:     Alberto da Silva
    Date:       10 April 2022
    Version:    0.9
    Note: mqtt_topic is not checked for "/" or incorrect input
    Only minimal checking of arguments is done
"""

import os
import argparse

import logging
import json
import serial
import paho.mqtt.client as mqtt
import juntek_kg
#from elapsed import Elapsed
import elapsed


# globals
instrument = None
args = None
logger = None
mqtt_client = None

def mqtt_publish(topic: str, payload: str, retain: bool = False, wait: bool = False) -> None:
    """publish payload on mqtt topic"""
    logger.debug("topic=%s, payload=%s", topic, payload)
    infot = mqtt_client.publish(topic=topic, payload=payload, qos=0, retain=retain)
    if wait:
        infot.wait_for_publish()

# https://developers.home-assistant.io/docs/core/entity/sensor/#available-device-classes
DEVICE_CLASS_DICT = {
    "A"  : "current",
    "V"  : "voltage",
    "W"  : "power",
    "°C" : "temperature",
    "Hz" : "frequency",
    "Ah" : "energy",
    "Wh" : "energy",
    "%"  : "battery",     # SoC
    "tm" : "timestamp"    # mdi:progress-clock
}

def get_device_class(key: str):
    """return device_class from the dict()"""
    return DEVICE_CLASS_DICT.get(key,None)

def mqtt_publish_hass_discovery(base_topic: str, sensors: dict, settings: dict):
    """
    HASS discovery - publish Juntek sensor information via mqtt
    topic & payload need to be formatted according to:
        https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
        https://developers.home-assistant.io/docs/core/entity
    for HASS to "discover" the sensor
    """

    # static information
    manufacturer = "Juntek"
    model = settings['model']
    sw_version = settings['version']
    hw_version = model + "_" + settings['sensor']
    device_name = f"Juntek_{model}" # display name
    device_id = settings['model'].lower()   # same in mqtt_publish_state()
    identifiers = [device_id]

    # for every register create a disovery_topic & discovery_payload, then mqtt_publish
    for key, value in sensors.items():
        name = key
        payload = value
        name = key                 # eg voltage, current, temperature
        state_name = key
        unit_of_measure = juntek_kg.JUNTEK_R50_DICT[name]['unit']
        unique_id = device_id + "_" + key # alphanumerics, underscore and hyphen only
        object_id = unique_id  # Best practice for entities with a unique_id is to set <object_id> to unique_id

        # <discovery_prefix>/<component>/[<node_id>/]<object_id>/config
        discovery_topic = "homeassistant/sensor/" + object_id + "/config"

        # state_topic - topic we use via mqtt_publish_state()
        state_topic = base_topic + "/" + device_id + "/" + state_name + "/state"

        # discovery payload is the register information + device(battery)
        discovery_payload = { "name": name,
                              "state_topic": state_topic,
                              "unit_of_measurement": unit_of_measure,
                              "unique_id": unique_id,
                              "object_id": object_id,
                              "device": {
                                        "identifiers": identifiers,
                                        "name": device_name,
                                        "model": model,
                                        "sw_version": sw_version,
                                        "hw_version": hw_version,
                                        "manufacturer": manufacturer
                                    }
                            }

        # add device_class to discovery payload
        device_class = get_device_class(unit_of_measure)
        if device_class:
            discovery_payload["device_class"] = device_class

        logger.info("discovery_topic=%s,\ndiscovery_payload=%s", discovery_topic, json.dumps(discovery_payload,indent=4))

        # publish discovery topic & payload with optional retained=True
        # retained=True to make mqtt retain discovery messages on restart
        if args.mqtt and args.mqtt_hass:
            mqtt_publish(topic=discovery_topic, payload=json.dumps(discovery_payload), retain=args.mqtt_hass_retain)


def mqtt_publish_state(base_topic: str, sensors: dict, settings: dict):
    """ loop thru sensors and publish via mqtt """
    device_id = device_id = settings['model'].lower()

    for key, value in sensors.items():
        state_name = key
        payload = value
        state_topic = base_topic + "/" + device_id + "/" + state_name + "/state"
        logger.info("state_topic=%s, payload=%s", state_topic, payload)
        if args.mqtt:
            mqtt_publish(state_topic, payload, False)



def setup_args() -> None:
    """ parse arguments """
    global args
    parser = argparse.ArgumentParser(description="Junek KG-F to HASS via MQTT example app")

    parser.add_argument("--device", help="RS485 device, e.g. /dev/ttyUSB1", type=str, required=True)
    parser.add_argument("--baudrate", help="RS485 baudrate, default=115200'", type=int, default=115200)
    parser.add_argument("--mqtt", help="MQTT enable message publish", action="store_true")
    parser.add_argument("--mqtt-user", help="MQTT username", type=str) # WARNING: passing passwords on cmd line is not secure
    parser.add_argument("--mqtt-password", help="MQTT password", type=str)
    parser.add_argument("--mqtt-broker", help="MQTT broker (server), default localhost", type=str, default="localhost")
    parser.add_argument("--mqtt-port", help="MQTT port, default 1883", type=int, default=1883)
    parser.add_argument("--mqtt-topic", help="MQTT topic, default 'juntek'", type=str, default="juntek")
    parser.add_argument("--mqtt-hass", help="MQTT enable Home Assistant discovery", action="store_true")
    parser.add_argument("--mqtt-hass-retain", help="MQTT enable retain HASS discovery mesages", action="store_true")
    parser.add_argument("--debug", help="Enable debug output", action="store_true")
    parser.add_argument("--sleep", help="Seconds bettwen sampling loop, default=60", type=int, default=60)

    args = parser.parse_args()

def setup_logger() -> None:
    """ setup logging """
    global logger

    level = logging.DEBUG if args.debug else logging.INFO
    logger = logging.getLogger(__name__)
    logging.basicConfig(format="%(asctime)s %(levelname)s [%(filename)s:%(lineno)s %(funcName)s()] %(message)s", level=level)

def setup_instrument() -> None:
    """ Open serial port """
    global instrument
    instrument = serial.Serial( port=args.device, baudrate=args.baudrate ) # timeout(float)
    logger.info("instrument=%s",instrument)

def setup_mqtt_client() -> None:
    """ connect to mqtt """
    global mqtt_client
    client_name = os.path.basename(__file__)
    logger.info("setup_mqtt_client: connecting=%s",args.mqtt_broker)
    mqtt_client = mqtt.Client(client_name)
    #mqtt_client.enable_logger(logger)
    mqtt_client.username_pw_set(args.mqtt_user, args.mqtt_password)
    mqtt_client.connect(args.mqtt_broker, port=args.mqtt_port)


def main() -> None:
    """ setup and loop """
    print("Juntek KG-F coloumb meter decoder to mqtt - Alberto - Apr 2022")

    setup_args()
    setup_logger()
    setup_instrument()
    if args.mqtt:
        setup_mqtt_client()
    
    jkg = juntek_kg.JuntekKG(instrument)

    loop_count = 0
    timer = elapsed.Elapsed(args.sleep)

    # READ LOOOP
    while True:
        line = instrument.readline()
        jkg.decode_line(line)
        if timer.check():
            sensors = jkg.get_sensors()
            logger.debug("sensors=%s",json.dumps(sensors, indent=4))

            # publish discovery first loop and every 15 loops
            if loop_count % 15 == 0:
                settings = jkg.get_settings()
                logger.debug("settings=%s",json.dumps(settings, indent=4))
                logger.info("publishing hass discovery")
                mqtt_publish_hass_discovery(args.mqtt_topic, sensors, settings)
                
            logger.info("publishing sensor data")
            mqtt_publish_state(args.mqtt_topic, sensors, settings)

            # run maintenance task to check SoC=100 and reset cumulative_Ah, charge_Wh, run_time_record
            jkg.run_maintenance()
            loop_count += 1
            logger.info("============= sleep %d, loop_count=%d, ===========", args.sleep, loop_count)

if __name__ == "__main__":
    main()