entropy
=======

Home energy monitor, with support for Rainforest Automation Raven USB radio, and exploring
different plotting systems. Dweet works, now trying plotly.

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

Installation
============
* FTDI USB driver - [read here](http://forums.whirlpool.net.au/archive/1928671).
* Edit config.ini to match your setup - serial port, etc.

Design of code
==============

1. The Raven device is serial over USB, so we read lines from it using PySerial
2. Fugly code to chunk up XML text before feeding it into Python's ElementTree
3. Convert to base 10, scale, convert timestamp
4. Send to plotter
6. Profit