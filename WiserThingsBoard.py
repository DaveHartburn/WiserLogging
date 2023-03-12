# WiserThingsBoard.py
import json
import paho.mqtt.client as mqtt
from pprint import pprint
import time

THINGSBOARD_PORT=1883
urls = {'mytelem': 'v1/devices/me/telemetry',
    'provision': 'v1/gateway/connect',
    'attrib': 'v1/gateway/attributes',
    'gwtelem': 'v1/gateway/telemetry'
        }
class WiserThingsBoard:
    def __init__(self, debugFunction, loggingFunction, tbServer, tbToken, tbPrefix, tbProfile):
        # Pass with references to the central debugging and logging functions
        # along with details needed to connect to the ThingsBoard server
        # tbPrefix is what to prefix all TB device names with
        self.debug=debugFunction
        self.logMessage=loggingFunction
        
        #self.debug(5, "Test debugging message from class")
        #self.logMessage("Test logging message from class")

        self.tbServer=tbServer
        self.tbToken=tbToken
        self.tbPrefix=tbPrefix
        self.tbProfile=tbProfile
        self.tbDevices=[]    # List to track ThingsBoard devices we have already created

        # 'global' variables
        self.mqtt_connected = False
        self.client = mqtt.Client()
        # Connect to the server
        self.mqttConnect()

    # Functions to log Wiser data into thingsboard
    def logToThingsBoard(self, hub, rooms):
        # Log all the gathered data into ThingsBoard
        
        self.debug(5, "Logging data to ThingsBoard")

        # Log hub data
        #print(hub)
        self.mqttPublish(urls["mytelem"], hub)

        for r in rooms:
            #self.debug(5, "  Inspecting room "+r)
            # Create name
            devName="{} room {}".format(self.tbPrefix, r)
            if not devName in self.tbDevices:
                self.logMessage("Room '"+devName+"' unknown during this run, creating")
                self.tbDevices.append(devName)

                msg="{{'device':'{}', 'type':'{}'}}".format(devName, self.tbProfile)
                self.client.publish(urls["provision"], msg)

                # Set device attributes
                msg="{{'{}':{{'Note':'Created by WiserLogging MQTT Gateway'}}}}".format(devName)
                self.client.publish(urls["attrib"], msg)
            #else:
            #    self.debug(5, "  We have already created this room")

            telemData=self.buildTelemSingle(devName, rooms[r])
            #self.debug(5, "Sending "+telemData)
            self.client.publish(urls["gwtelem"], telemData)

    # End of logToThingsBoard()

    def buildTelemSingle(self, devName, tdata):
        # Build telemetry from a dictionary, in the format MQTT expects
        # Returns as a JSON string
        ##pprint(tdata)
        timeSeries={devName:[
            {"ts": int(time.time()*1000),
             "values": tdata}
        ]}
        return(json.dumps(timeSeries))

    # MQTT utility functions
    def on_connect(self, client, userdata, flags, rc):
        if(rc==0):
            self.mqtt_connected = True
            self.debug(5, "MQTT server connected successfully")
        else:
            self.mqtt_connected = False
            self.debug(5, "MQTT server failed to connect rc={}".format(rc))

    def on_disconnect(self, client, userdata, rc):
        self.mqtt_connected = False
        self.debug(5, "MQTT server disconnected, rc={}".format(rc))

    def on_publish(self, client, userdata, mid):
        #self.debug(5, "MQTT on_publish returned {}".format(mid))
        pass

    def mqttConnect(self):
        # Connect to thingsboard server
        self.debug(5, "Connecting to ThingsBoard server")
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        #self.client.on_publish = self.on_publish
        self.client.username_pw_set(self.tbToken)
        self.debug(5, "Connecting to {}, port {}, token {}".format(self.tbServer, THINGSBOARD_PORT, self.tbToken))
        try:
            self.client.connect(self.tbServer, THINGSBOARD_PORT, 60)
        except:
            print("Error: exception when connecting to MQTT server")
        self.client.loop_start()                

    def mqttDisconnect():
        # Close down thingsboard session
        self.client.loop_stop()
        self.client.disconnect()
        self.mqtt_connected = False

    def mqttPublish(self, url, data):
        # Publish data to the URL, where data is a python structure not a JSON string
        # Check to see if we are connected
        if(self.mqtt_connected==False):
            self.mqttConnect()

        self.debug(5, "Publishing to "+url)
        self.client.publish(url, json.dumps(data))
        

# End of WiserThingsBoard class