# WiserLogging
Log temperatures and events from a Drayton Wiser home heating system

Objectives
  *  Obtain a list of room temperatures and graph via ThingsBoard
  *  Report individual battery levels and graph them
  *  Report when each radiator requests heat and opens the valve
  *  Report when the boiler fires up
  *  When do radiators go into eco mode / open windows detected?
  *  Set up timed automations, e.g. Away mode for 4 hours
  *  Advanced control of one radiator valve which doesn’t seem to turn one radiator off
  *  Essentially produce a log of day to day activities

## Installing the API Library 

This project uses the API library from Angelo Santagata https://github.com/asantaga/wiserheatingapi
* In a temporary directiory: `git clone https://github.com/asantaga/wiserheatingapi`
* sudo python3 setup.py install

## Other dependencies
paho-mqtt `apt install python3-paho-mqtt`

## Running this library

Populate the wiserkeys.params file as described in the above repository.

Run WiserLogger.py



## My notes
Logging
https://www.loggly.com/use-cases/python-syslog-how-to-set-up-and-troubleshoot/
https://signoz.io/blog/python-syslog/
