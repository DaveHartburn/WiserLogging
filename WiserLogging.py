#!/usr/bin/python3

# WiserLogging
# A python script to log temperatures from a Drayton Wiser home heating system into ThingsBoard
# and to record events into a local syslog
#
# By Dave Hartburn March 2023

DEBUG=5             # Debug level to display, 1-5

def debug(level, msg):
    if(level<=DEBUG):
        print("WiserLogging({}): {}".format(level, msg))

debug(5, "Starting WiserLogging")