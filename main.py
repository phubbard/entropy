#!/usr/bin/env python

"""
@author Paul Hubbard
@date 5/7/14
@file main.py
@brief Starting new project for home energy monitoring, using various graphing systems.

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
import plotly.tools as tls
import plotly.plotly as py  
from plotly.graph_objs import *

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

def loop(serial, plotly_stream):
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
#        try:
#            requests.post('https://dweet.io/dweet/for/42df176b534c415e9681df5e28e348b1',
#                      params=demand)
#        except ConnectionError, ce:
#            log.warn('Unable to dweet')

        # Off to plotly too
        # TODO return pre-set X and Y from process_demand
        x = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
        y = float(demand['demand'])
        datum = dict(x=x, y=y)
        log.debug(datum)
        plotly_stream.write(datum)

def plot_two(stream_id):
    # REMOVE BEFORE COMMIT
    py.sign_in("phubbard", "g80698grqg")

    trace1 = Scatter(x=[], y=[], stream=dict(token=stream_id))
    data = Data([trace1])
    py.plot(data, filename='raven')
    s = py.Stream(stream_id)
    s.open()
    return s

def plot_setup(stream_id):

    stream = Stream(token=stream_id, maxpoints=80)
    trace1 = Scatter(x=[], y=[], stream=stream, mode='lines+markers')
    data = Data([trace1])

    # REMOVE BEFORE COMMIT
    py.sign_in("phubbard", "g80698grqg")

    layout = Layout(title='Electricity demand')
    fig = Figure(data=data, layout=layout)
    new_url = py.plot(fig, filename='raven')
    
    log.info(new_url)
    s = py.Stream(stream_id)
    s.open()
    return s

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

    log.info('Opening plot.ly...')
    strm = plot_two(cf.get('plotly', 'stream_id'))

    loop(serial_port, strm)

if __name__ == '__main__':
    setup()
