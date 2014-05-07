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

from version import VERS_STR


def do_chunk(serial, mqtt, graphite, topic):
    """
    Key routine - chunk up the serial data, feed it to the XML parser,
    broadcast the results.
    """

    buf = ''
    while True:
        in_buf = serial.readline().strip()
        buf += in_buf
        log.debug(in_buf)

        if in_buf == '</CurrentSummationDelivered>' or in_buf == '</InstantaneousDemand>':
            try:
                elem = ET.fromstring(buf)
            except ET.ParseError:
                log.warn('Parser error, ignoring: ' + buf)
                buf = ''
                continue

            # Parsed OK
            broadcast(process_reading(elem), mqtt, topic, graphite)
            return


def broadcast(datum, broker, topic, graphite):
    """
    Given a datum, send it out to MQTT broker and/or graphite, if they
    are available. Also logs to screen.
    """

    if datum == None:
        return

    log.info(datum)

    if broker is not None:
        broker.publish(topic, str(datum))
    if graphite is not None:
        graphite.send(topic, datum, timestamp=datum['at'])


def get_decimal_subelement(elem, tag):
    """
    For an Element, find the proper tag, convert from hex to decimal.
    Data from the Raven looks like
      <SummationDelivered>0x0000000001a4b8bb</SummationDelivered>
    so we need to convert that hex string into an integer. Voila.
    """
    return int(elem.find(tag).text, 16)


def process_reading(elem):
    """
    For either a InstantaneousDemand or CurrentSummationDelivered element,
    parse, convert and return a dictionary with value and timestamp.
    Convert to decimal,
    shift timestamp, do proper scaling. Code borrows heavily from the
    raven-cosm project.
    """

    # These elements are common to both
    seconds_since_2000 = get_decimal_subelement(elem, 'TimeStamp')
    multiplier = get_decimal_subelement(elem, 'Multiplier')
    divisor = get_decimal_subelement(elem, 'Divisor')
    epoch_offset = calendar.timegm(time.strptime("2000-01-01", "%Y-%m-%d"))
    gmt = datetime.datetime.utcfromtimestamp(seconds_since_2000 + epoch_offset).isoformat()

    # Now we branch
    if elem.tag == 'InstantaneousDemand':
        demand = get_decimal_subelement(elem, 'Demand')
        return ({"at": gmt +'Z', "demand": str(1000.0 * demand * multiplier / divisor)})
    elif elem.tag == 'CurrentSummationDelivered':
        sum_delivered = get_decimal_subelement(elem, 'SummationDelivered')
        sum_received = get_decimal_subelement(elem, 'SummationReceived')
        difference = sum_delivered - sum_received
        return({"at": gmt +'Z', "summation": str(1000.0 * difference * multiplier / divisor)})

    log.warn('Unknown element ' + elem.tag)


def main():
    log.basicConfig(level=log.INFO, format='%(asctime)s %(levelname)s [%(funcName)s] %(message)s')

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
        mqtt = paho.Client(VERS_STR, False)
        mqtt.connect(cf.get('mqtt', 'host'), cf.getint('mqtt', 'port'))
        mqtt.publish(topic, VERS_STR + ' starting up', 0, retain=False)
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

    log.info('Loop starting')
    while True:
        do_chunk(serial_port, mqtt, g, topic)


if __name__ == '__main__':
    main()