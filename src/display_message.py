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
import os
import uuid
import configparser
import RPi.GPIO as GPIO
import time

config = configparser.ConfigParser()
config.read('config.ini')

_HOSTNAME = config['broker']['hostname']
_PORT = 443
_CLIENTID = "ntdc-iorus-"+str(uuid.uuid1())
_USERNAME = config['broker']['username']
_PASSWORD = config['broker']['password']
_TOPIC = "iorus/message"

GPIO.setmode(GPIO.BCM)   # mode de numérotation des pins pour le gyrophare

global message
message = ""

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
	print("Client "+_CLIENTID+" connected with result code "+str(rc))
	print "------------------------------"
	# Subscribing in on_connect() means that if we lose the connection and
	# reconnect then subscriptions will be renewed.
	client.subscribe(_TOPIC,1)
	try:
		os.system("sudo python /home/pi/rpi-rgb-led-matrix/bindings/python/samples/runtext.py --led-no-hardware-pulse=true --led-chain=2 --led-slowdown-gpio 2 -t='IORUS ready' -co='green'")
	except MatrixError:
		print("Erreur lors de l'affichage du dernier message")
		pass
	finally:
		print message

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
	print "==="
	print("Topic : "+msg.topic+" | Message : "+str(msg.payload))
	print "==="
	
	global message
	global criticite
	global color

	payload = json.loads(str(msg.payload))
	message = unicodedata.normalize('NFD', payload['message']).encode('ascii', 'ignore')
	criticite = payload['criticite']
	
	# ===========================
	# Initialisation du Gyrophare
	# ===========================
	
	
	if criticite == "1":
		color = "red"
		print ("HIGH")
		GPIO.setup(21,GPIO.OUT)  # le pin 21 réglée en sortie (output)
		GPIO.output(21,GPIO.HIGH)
		time.sleep(2)
	elif criticite == "2":
		color = "orange"
		GPIO.setup(21,GPIO.OUT)  # le pin 21 réglée en sortie (output)
		GPIO.output(21,GPIO.HIGH)
		time.sleep(2)
	elif criticite == "3":
		color = "blue"
		GPIO.setup(21,GPIO.OUT)  # le pin 21 réglée en sortie (output)
		GPIO.output(21,GPIO.HIGH)
		time.sleep(2)
		GPIO.cleanup(21)
	else:
		color = "green"

	try:
		os.system("sudo python /home/pi/rpi-rgb-led-matrix/bindings/python/samples/runtext.py --led-no-hardware-pulse=true --led-chain=2 --led-slowdown-gpio 2 -t='"+str(message)+"' -co='"+str(color)+"'")
		if criticite == "1" or criticite == "2":
			GPIO.cleanup(21)
			
	except MatrixError:
		print("Erreur lors de l'affichage du dernier message")
		pass
	finally:
		print message

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
client = mqtt.Client(_CLIENTID, False, None, "MQTTv311", "websockets")
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

