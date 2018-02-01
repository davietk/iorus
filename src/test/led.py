#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test d'allumage d'une LED via les GPIO
Détail technique GPIO : https://i.stack.imgur.com/yWGmW.png

:author kevin.daviet@accenture.com
:date 27/11/2017
:version 1.0
"""

import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)   # mode de numérotation des pins
GPIO.setup(25,GPIO.OUT)  # la pin 25 réglée en sortie (output)

if __name__ == '__main__':

	GPIO.output(25,GPIO.HIGH)   # sortie au niveau logique haut (3.3 V)
	sleep(500)					# attente de 5 secondes
	GPIO.output(25,GPIO.LOW)    # sortie au niveau logique bas (0 V)
