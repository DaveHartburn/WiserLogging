#!/usr/bin/python3

# WiserLogging
# A python script to log temperatures from a Drayton Wiser home heating system into ThingsBoard
# and to record events into a local syslog
#
# By Dave Hartburn March 2023

from wiserHeatingAPI import wiserHub
import sys
import json
import time
from pprint import pprint
import WiserThingsBoard

DEBUG=5             # Debug level to display, 1-5
loopWait=120        # Seconds between data checks and upload
tbNamePrefix="Wiser"    # Device name to prefix all created devices with
tbProfile="Wiser"


def debug(level, msg):
    if(level<=DEBUG):
        print("WiserLogging({}): {}".format(level, msg))

debug(2, "Starting WiserLogging")

# ********** Functions *************
def logMessage(msg):
    # Log an event in the log file
    # *** Not properly implemented!
    print("LOG: "+msg)

def ooToInt(instr):
    # Takes a string, expected to be On or Off and returns 0 (off) 1 (on) -1 (unknown)
    if(instr.lower()=="on"):
        return 1
    elif(instr.lower()=="off"):
        return 0
    else:
        return 1

def intToOo(i):
    # Opposite of ooToInt, 0->'Off',1->'On' or 'Unknown'
    if(i==0):
        return 'Off'
    elif(i==1):
        return 'On'
    else:
        return 'Unknown'




# ********** End of functions **********



# Get Wiser Parameters from keyfile
try:
    with open("wiserkeys.params", "r") as f:
        data = f.read().split("\n")
    wiserkey = ""
    wiserip = ""
    tbServer = ""
    tbToken = ""
except:
    print("ERROR: Unable to open wiserkeys.params file. Make sure it exists and has correct permissions")
    exit(1)

# Get wiserkey/hubIp from wiserkeys.params file
# This file is not source controlled as it contains the testers secret etc

for lines in data:
    line = lines.split("=")
    if line[0] == "wiserkey":
        wiserkey = line[1]
    if line[0] == "wiserhubip":
        wiserip = line[1]
    if line[0] == "tbserver":
        tbServer = line[1]
    if line[0] == "tbtoken":
        tbToken = line[1]
#print(" Wiser Hub IP= {} , WiserKey= {}".format(wiserip, wiserkey))
if(wiserkey=="" or wiserip==""):
    print("ERROR: No wiserkey or wiserip set in wiserkeys.params file, unable to continue")
    exit(1)
if(tbServer=="" or tbToken==""):
    print("ERROR: No tbserver or tbtoken set in wiserkeys.params file, unable to continue")
    exit(1)

debug(5, "Key file opening, attempting to connect to hub")

# Build data structures, one for the basic hub data, one for each room and
# one for each device, to report each device bettery level and status
hubData={'heating':-1, 'hotwater':-1}
rooms={}
devices={}
devToRoom={}    # Keep track of devices in each room

# Start ThingsBoard Logging class
TB=WiserThingsBoard.WiserThingsBoard(debug, logMessage, tbServer, tbToken, tbNamePrefix, tbProfile)

try:
    wh = wiserHub.wiserHub(wiserip, wiserkey)
    debug(1, "Successfully connected to Wiser Hub, model {}".format(wh.getWiserHubName()))

    # Start main loop
    while True:
        dataIn=wh.getHubData()
        # Set the heating relay status. This assumes one heating channel
        hc=ooToInt(dataIn["HeatingChannel"][0]["HeatingRelayState"])
        if(hubData['heating']!=hc):
            logMessage("Heating relay changed from {} to {}".format(intToOo(hubData['heating']), intToOo(hc)))
            hubData['heating']=hc
        hw=ooToInt(dataIn["HotWater"][0]["HotWaterRelayState"])
        if(hubData['hotwater']!=hw):
            logMessage("Heating relay changed from {} to {}".format(intToOo(hubData['hotwater']), intToOo(hw)))
            hubData['hotwater']=hw

        # Build room data structure.
        # If a room has more than one device in it, multiple rooms are created
        # We build a new structure and compare it to the previous
        newRooms={}
        for r in dataIn['Room']:
            # For each room we want to gather:
            #  Name, Temperature, Open Window, Requesting Heat
            name=r["Name"]
            temp=r["CalculatedTemperature"]/10
            # Rooms without a TRV don't detect open windows
            # Set a text string for nicer output, but also a numeric value, 0 closed, 1 open
            if "WindowState" in r:
                windowStr=r["WindowState"]
                if(windowStr=="Closed"):
                    window=0
                else:
                    window=1
            else:
                windowStr="Unknown"
                window=-1

            # Every room should have ControlOutputState (heat request), but to be sure
            if "ControlOutputState" in r:
                heatReqStr=r["ControlOutputState"]
                heatReq=ooToInt(heatReqStr)
            else:
                heatReqStr="Unknown"
                heatReq=-1
            # Build temporary room data structure
            rd={'name':name, 'temperature': temp, 'windowStr': windowStr, 'window': window, 'heatReqStr': heatReqStr, 'heatReq':heatReq}
            debug(5,"Room:"+str(rd))
           
            # Compare to last run, if room exists from previous. We may have just added a new room
            if name in rooms:
                # Did exist last time
                if(rooms[name]["windowStr"]!=rd["windowStr"]):
                    logMessage("Window state in room {} changed from {} to {}".format(name, rooms[name]["windowStr"], rd["windowStr"]))
                if(rooms[name]["heatReq"]!=rd["heatReq"]):
                    if(rd["heatReq"]==0):
                        logMessage("{} stopped requesting heat, temperature is {}".format(name, temp))
                    else:
                        logMessage("{} requested heat, temperature is {}".format(name, temp))

            # Track the devices in each room
            devCount=0
            devsInRoom=[]
            if("RoomStatId" in r):
                #debug(5,"*** Room {} has a thermostat".format(name))
                devCount+=1
                devToRoom[r["RoomStatId"]]=name
                devsInRoom.append(r["RoomStatId"])
            if("SmartValveIds" in r):
                #debug(5,"  Room {} has smart valves".format(name))
                devCount+=len(r["SmartValveIds"])
                for i in r["SmartValveIds"]:
                    devToRoom[i]=name
                    devsInRoom.append(i)
            # Add number of devices to data structure
            rd["deviceCount"]=devCount
            
            # Save to new data structure
            if(devCount==1):
                # Save device under that name
                newRooms[name]=rd
            else:
                # Save room multiple times for each ID
                for i in devsInRoom:
                    newName="{} #{}".format(name, i)
                    # Avoid linked records
                    unlinkedRD=rd.copy()
                    newRooms[newName]=unlinkedRD
                    # Update devToRooms with new name
                    devToRoom[i]=newName
        # End of rooms loop
        #debug(5, "devToRoom = "+str(devToRoom))

        # Save newRooms to rooms
        rooms=newRooms
        #pprint(rooms)

        # Process devices
        #debug(5, "Processing devices....")
        # We don't report changes in devices. Blow away old list so offline device doesn't become 'sticky'

        for d in dataIn["Device"]:
            #debug(5, "  Inspecting ID {}, type {}".format(d["id"],d["ProductType"]))
            # Only report iTRVs and RoomStats
            if(d["ProductType"]=="RoomStat" or d["ProductType"]=="iTRV"):
                # Find room
                rm=devToRoom[d["id"]]
                devCount=rooms[rm]["deviceCount"]
                #debug(5, "    It is in room {}, number of devices={}".format(rm,devCount))
                # Add data to the room data

                # This should always have a bettery voltage, but occasionally throws an error
                # when this key is missing.
                try:
                    rooms[rm]["batteryVoltage"]=d["BatteryVoltage"]/10
                    rooms[rm]["batteryStatus"]=d["BatteryLevel"]
                    rooms[rm]["productType"]=d["ProductType"]
                    rooms[rm]["deviceId"]=d["id"]
                except KeyError as err:
                    logMessage("Warning: Key error checking device details in room {}: {}".format(rm, err))
       # End of devices loop

        # Add temperatures from individual smmart valves
        #debug(5, "Processing smart valves....")
        for sm in dataIn["SmartValve"]:
            id=sm["id"]
            rm=devToRoom[sm["id"]]
            #debug(5, "Looking at smart valve id {} in room {}".format(id, rm))
            # Add iTRV temperature to the room
            rooms[rm]["iTRVtemperature"]=sm["MeasuredTemperature"]/10
            #debug(5, "Setting room '{}' iTRVtemperature to {}".format(rm, sm["MeasuredTemperature"]/10))

        TB.logToThingsBoard(hubData, rooms)

        time.sleep(loopWait)
        wh.refreshData()
    # End of main loop

except Exception as err:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    debug(1, "Error: {}, {} at line number {}".format(err,type(err),exc_tb.tb_lineno))
    
