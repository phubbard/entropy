entropy
=======

Home energy monitor, with support for Rainforest Automation Raven USB radio, Graphite and MQTT

This is scratching a personal itch. I have working code to stream Raven
data to Xively, but I'm not happy with the current iOS and Android clients,
I want a better way to share graphs/data, and I want to add solar data
as well.

Hardware requirements
=====================

* [Rainforest Automation Raven RFA-Z106](http://rainforestautomation.com/raven) or compatible
* Compatible smart power meter

Software requirements
=====================

* See requirements.txt. I assume you're using virtualenv and Pip.
* (Optional) [MQTT server](http://mqtt.org/wiki/doku.php/brokers), for pushing data to mobile and web clients
* (Optional) [Graphite](http://graphite.readthedocs.org/en/latest/index.html) server, for logging and plotting and sharing

Installation
============
* FTDI USB driver - [read here](http://forums.whirlpool.net.au/archive/1928671).
* Edit config.ini to match your setup - serial port, etc.

Design of code
==============

1. The Raven device is serial over USB, so we read lines from it using PySerial
2. Fugly code to chunk up XML text before feeding it into Python's ElementTree
3. Convert to base 10, scale, convert timestamp
4. Send to MQTT (if enabled)
5. Send to Graphite (if enabled)
6. Profit