#!/usr/bin/env python
# Super simple script that listens to a local UDP port and relays all packets to an arbitrary remote host.
# Packets that the host sends back will also be relayed to the local UDP client.
# Works with Python 2 and 3
# script is taken from here: https://github.com/EtiennePerot/misc-scripts/blob/master/udp-relay.py and has been
# Updated to add the following functions
# Multiple Clients can have their individual Packets relayed to the arbitrary remote host.
# host replies to a specific client is re-routed back to that specific client

import sys, socket, select, time, math

# Whether or not to print the IP address and port of each packet received
debug=False

def fail(reason):
	sys.stderr.write(reason + '\n')
	sys.exit(1)

if len(sys.argv) != 2 or len(sys.argv[1].split(':')) != 3:
	fail('Usage: udp-relay.py localPort:remoteHost:remotePort')

localPort, remoteHost, remotePort = sys.argv[1].split(':')

try:
	localPort = int(localPort)
except:
	fail('Invalid port number: ' + str(localPort))
try:
	remotePort = int(remotePort)
except:
	fail('Invalid port number: ' + str(remotePort))

try:
	mainS = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	mainS.bind(('', localPort))
except:
	fail('Failed to bind on port ' + str(localPort))

inputConns = [mainS]
connectedClients = [] 
lastPingReceived = []
activityStart = []

#list of connected clients: 
knownServer = (remoteHost, remotePort)
sys.stdout.write('All set, listening on '+str(localPort)+'.\n')

while True:
	if debug:
		print("\tConn Size "+str(len(inputConns)))
	#receive connected client data from the main
	readable, writable, execeptions = select.select(inputConns, [], [])
	for s in readable:
		if s is mainS:
			clientData, client_address = s.recvfrom(32768)
			if client_address not in connectedClients:
				print("New Client connected: "+ str(client_address))
				connectedClients.append(client_address)
				lastPingReceived.append(time.time())
				activityStart.append(time.time())
				#create a new outgoing socket for the new client
				try:
					newClientS = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
					newClientS.bind(('',0))#bind to any port
					inputConns.append(newClientS)
					print("\tCreated new Socket Connection for client "+newClientS.getsockname()[1])
				except:
					fail('Couldnt create connection for new client '+str(client_address))
			
			#send received data to remote server through the right client socket
			if debug:
				print("\tforwarding data from client "+str(client_address)+" to HV "+str(knownServer))
			clientID = connectedClients.index(client_address)
			lastPingReceived[clientID] = time.time()
			if debug:
				print("\tClient ID: "+str(clientID))
			inputConns[clientID+1].sendto(clientData, knownServer)

		#receive data for client from remote server
		else:
			clientID = inputConns.index(s)-1
			hvdata, vpn_adress_most_likely = s.recvfrom(32768)
			mainS.sendto(hvdata, connectedClients[clientID])
			if debug:
				print("\tforwarding data from HV "+str(vpn_adress_most_likely)+" to client "+str(connectedClients[clientID]))

	timedOutIDs = []
	now = time.time()
	for s in lastPingReceived:
		if now - s > 30:
			timedOutIDs.append(lastPingReceived.index(s))

	#cleaning up timed out connections
	for delIDs in timedOutIDs:
		if True:
			print("\tCleaning up "+str(connectedClients[delIDs]) +" for inactivity ")
			activityLength = math.floor((time.time()-activityStart[delIDs])/60)
			print("\tActive for "+str(activityLength)+" minutes")
		inputConns[delIDs+1].close()
		del inputConns[delIDs+1]
		del connectedClients[delIDs]
		del lastPingReceived[delIDs]
		del activityStart[delIDs]
