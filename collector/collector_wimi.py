#!/usr/bin/python
# coding: utf-8

import configparser, unicodedata, requests
from pywimi import wimi

config = configparser.ConfigParser()
config.read('collector_config.ini')

# Connexion à l'instance Wimi
wimi.log_in(config['wimi']['instance'], config['wimi']['login'], config['wimi']['password'], "lot-5-tmt", config['wimi']['app_token'])

# Récupération des taches de la liste Notification
# notification_list_id = wimi.getTaskListId("Notification")
tasks_list = wimi.listTask(wimi.getTaskListId("Notification"))
for task in tasks_list:

	message = unicodedata.normalize('NFD', task['label']).encode('ascii', 'ignore')
	criticite = task['description']

	if criticite == "":
		criticite = 3

	print ("https://www.ntdc-demos.tk/node-red/node/iorus?message="+str(message)+"&criticite="+str(criticite))

	# Appel du endpoint pour envoi du message
	result = requests.get("https://www.ntdc-demos.tk/node-red/node/iorus?message="+str(message)+"&criticite="+str(criticite), auth=(config['nodered']['login'], config['nodered']['password']))
	print (str(result))

	# Suppression de la tache une fois quelle a été affiché
	wimi.deleteTask(task['task_id'])

# Déconnexion
wimi.log_out()
