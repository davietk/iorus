#!/bin/sh

cd /home/pi

echo "Récupération du projet hzeller"
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd /home/pi/rpi-rgb-led-matrix/bindings/python
make build-python
sudo make install-python

echo "Déplacement du script d'affichage du texte modifié"
mv /home/pi/rpi-rgb-led-matrix/bindings/python/samples/runtext.py /home/pi/rpi-rgb-led-matrix/bindings/python/samples/runtext.py.old
cp /home/pi/iorus/src/runtext.py.copy /home/pi/rpi-rgb-led-matrix/bindings/python/samples/runtext.py

echo "Installation des packages python"
pip install paho-mqtt==1.2
pip install certifi
pip install configparser