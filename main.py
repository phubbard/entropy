#!/usr/bin/env python

"""
@author Paul Hubbard
@date 5/7/14
@file main.py
@brief Starting new project for home energy monitoring, using Graphite plus MQTT.

"""

import json
import datetime
import calendar
import time
from ConfigParser import SafeConfigParser
from xml.etree import ElementTree as ET
import logging as log
import sys

import serial
import graphitesend
import paho.mqtt.client as paho

from version import VERSION


def get_demand_chunk(serial):

    buf = ''
    in_element = False

    while True:
        in_buf = serial.readline()
        log.debug('>' + in_buf)

        if not in_element:
            if in_buf == '<InstantaneousDemand>':
                in_buf = True
                buf += in_buf
                continue
            else: # Keep waiting for start of element we want
                continue

        if in_element:
            buf += in_buf

        if in_buf == '</InstantaneousDemand>':
            return buf

def process_demand(elem):
    """
    Process the InstantaneoousDemand element - convert to decimal,
    shift timestamp, do proper scaling. Code borrows heavily from the
    raven-cosm project.
    """

    seconds_since_2000 = int(elem.get('TimeStamp'), 16)
    demand = int(elem.get('Demand'), 16)
    multiplier = int(elem.get('Multiplier'), 16)
    divisor = int(elem.get('Divisor'), 16)
    epoch_offset = calendar.timegm(time.strptime("2000-01-01", "%Y-%m-%d"))
    gmt = datetime.datetime.utcfromtimestamp(seconds_since_2000 + epoch_offset).isoformat()
    if seconds_since_2000 and demand and multiplier and divisor:
        return({"at": gmt +'Z', "demand": str(1000.0 * demand * multiplier / divisor)})

def loop(serial, mqtt, graphite, mqtt_topic='/paul'):
    """
    Read a chunk, buffer until complete, parse and send it on.
    """

    log.info('Loop starting')

    while True:
        log.debug('reading from serial')
        data_chunk = get_demand_chunk(serial)
        log.debug('Parsing XML')
        elem = ET.fromstring(data_chunk)
        demand = process_demand(elem)

        if mqtt is not None:
            log.debug('sending to mqtt')
            mqtt.publish(mqtt_topic, json.dumps(demand))
            mqtt.loop()

        if graphite is not None:
            log.debug('graphite send')
            graphite.send('demand', demand['demand'], timestamp=demand['at'])

def setup():
    log.basicConfig(level=log.DEBUG, format='%(asctime)s %(levelname)s [%(funcName)s] %(message)s')

    cfg_file = 'config.ini'
    if (len(sys.argv) == 2):
        cfg_file = sys.argv[1]

    log.info('Reading configuration file ' + cfg_file)
    cf = SafeConfigParser()
    cf.read(cfg_file)
    log.info('Opening Raven...')
    serial_port = serial.Serial(cf.get('raven', 'port'), cf.getint('raven', 'baud'))

    if cf.has_section('mqtt'):
        log.info('Opening MQTT connection...')
        topic = cf.get('mqtt', 'topic')
        mqtt = paho.Client('Entropy v' + VERSION, False)
        mqtt.connect(cf.get('mqtt', 'host'), cf.getint('mqtt', 'port'))
        mqtt.publish(topic, 'Entropy v' + VERSION + ' starting up', 0, retain=False)
        mqtt.loop()
    else:
        mqtt = None
        topic = None

    if cf.has_section('graphite'):
        log.info('Opening Graphite connection...')
        g = graphitesend.init(graphite_server=cf.get('graphite', 'host'),
                          graphite_port=cf.getint('graphite', 'port'))
    else:
        g = None

    loop(serial_port, mqtt, g, mqtt_topic=topic)
