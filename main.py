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
import requests

from version import VERSION


def get_demand_chunk(serial):

    buf = ''
    in_element = False

    while True:
        in_buf = serial.readline()
        in_buf_stripped = in_buf.strip()
        log.debug('>' + in_buf_stripped)

        if not in_element:
            if in_buf_stripped == '<InstantaneousDemand>':
                in_element = True
                buf += in_buf
                continue
            else: # Keep waiting for start of element we want
                continue

        if in_element:
            buf += in_buf

        if in_buf_stripped == '</InstantaneousDemand>':
            log.debug('got end of xml')
            return buf

def process_demand(elem):
    """
    Process the InstantaneoousDemand element - convert to decimal,
    shift timestamp, do proper scaling. Code borrows heavily from the
    raven-cosm project.
    """

    seconds_since_2000 = int(elem.find('TimeStamp').text, 16)
    demand = int(elem.find('Demand').text, 16)
    multiplier = int(elem.find('Multiplier').text, 16)
    divisor = int(elem.find('Divisor').text, 16)
    epoch_offset = calendar.timegm(time.strptime("2000-01-01", "%Y-%m-%d"))
    gmt = datetime.datetime.utcfromtimestamp(seconds_since_2000 + epoch_offset).isoformat()
    if seconds_since_2000 and demand and multiplier and divisor:
        return({"at": gmt +'Z', "demand": str(1000.0 * demand * multiplier / divisor)})

def loop(serial):
    """
    Read a chunk, buffer until complete, parse and send it on.
    """

    log.info('Loop starting')

    while True:
        log.debug('reading from serial')
        data_chunk = get_demand_chunk(serial)
        log.debug('Parsing XML')
        try:
            elem = ET.fromstring(data_chunk)
            demand = process_demand(elem)
        except:
            log.info('Ignoring parse errors')
            continue

        # TODO read dweet thing name from config.ini
        requests.post('https://dweet.io/dweet/for/42df176b534c415e9681df5e28e348b1',
                      params=demand)

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
    loop(serial_port)

if __name__ == '__main__':
    setup()
