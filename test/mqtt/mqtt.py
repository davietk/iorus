#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
import ssl
import logging
import datetime
import time
import sys
import json
import unicodedata

_HOSTNAME = ""
_PORT = 443
_CLIENTID = ""
_USERNAME = ""
_PASSWORD = ""
_TOPIC = ""

global message
message = ""

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
	print("Connected with result code "+str(rc))
	print "------------------------------"
	# Subscribing in on_connect() means that if we lose the connection and
	# reconnect then subscriptions will be renewed.
	client.subscribe(_TOPIC,1)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
	print "==="
	print("Topic : "+msg.topic+" | Message : "+str(msg.payload))
	print "==="
	global message
	message = str(msg.payload)

# Fonction deconnexion broker
def on_disconnect(client, userdata, rc):
	print("on_disconnect")
	if rc != 0:
		print("Unexpected disconnection.")
		print (client)
		print (userdata)
		print (rc)
	else:
		print("Deconnexion")

# ================================================================================================
# MAIN
# ================================================================================================

# Config client
client = mqtt.Client(_CLIENTID, False, None, "MQTTv311", transport="websockets")
# Path du certificat
client.tls_set("/etc/ssl/certs/ca-certificates.crt")
# Connexion /Reconnexion
client.on_connect = on_connect
# Réception message
client.on_message = on_message
# Déconnexion
client.on_disconnect = on_disconnect
# Credentials
client.username_pw_set(_USERNAME, _PASSWORD)

try:
	# Connexion / écoute de message
	client.connect(_HOSTNAME, _PORT)

except Exception, e:
  logging.error("Cannot connect to MQTT broker at %s:%d: %s" % (_HOSTNAME, _PORT, str(e)))
  # Waiting error
  raise
except KeyboardInterrupt:
  logging.error("User KeyboardInterrupt")
  # Clear screen
  raise

# Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a manual interface.
client.loop_forever()
#client.loop_start()
