#!/usr/bin/env python2
# -*- coding: utf-8 -*-

#
# watbot par aurelien.aptel@gmail.com
#

### install des deps (root)
# pip install sleekxmpp

### usage
# ./democracybot.py  -n democracy-bot -r 'lafamille@conference.babare.dynamic-dns.net' -j 'babar-bot@babare.dynamic-dns.net' -p password

REFERENDUM_RX = u'^r[é|e]f[é|e]rendum\s+[!|.]+'
YES_RX = r'o+u+i+\s*[!|.]*$'
NO_RX = r'n+o+n+\s*[!|.]*$'
BLANK_RX = r'b+l+a+n+c+\s*[!|.]*$'
RESULTAT_RX = u'r[é|e]sultat\s*[!|.]*'
QUESTION_RX = u'question\s*[!|.]*'

VOTE_DURATION = 60

import sys
import logging
import getpass
from optparse import OptionParser
import re
import sleekxmpp
import math
import threading
from datetime import datetime

if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')
else:
    raw_input = input


class MUCBot(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password, room, nick):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.last_msg = ''
        self.room = room
        self.nick = nick
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("groupchat_message", self.muc_message)
        self.referendumStarted = False
        self.questionAsked = False
        self.referendumOwner = None
        self.referendumOwnerNick = None
        self.question = ''
        self.votingUrn = dict()

    def start(self, event):
        self.get_roster()
        self.send_presence()
        self.plugin['xep_0045'].joinMUC(self.room,
                                        self.nick,
                                        # If a room password is needed, use:
                                        # password=the_room_password,
                                        wait=True)
    def startTimer(self):
        threading.Timer(VOTE_DURATION, self.timerEnd).start() 
        
    def timerEnd(self):
        print "timerEnd"
        self.sendMucMessage("Le vote est maintenant terminé.");
        self.sendMucMessage("La question était : \"" + self.question + "\"");
        self.sendResult()
        self.referendumStarted = False
        self.questionAsked = False
        self.votingUrn.clear()
	
    def sendMucMessage(self, msgStr):
        self.send_message(mto=self.room, mbody=msgStr, mtype='groupchat') 
        
                  
    def sendResult(self):
        yesCount = sum( vote == 'yes' for vote in self.votingUrn.values() )
        noCount = sum( vote == 'no' for vote in self.votingUrn.values() )
        blankCount = sum( vote == 'blank' for vote in self.votingUrn.values() )
        self.sendMucMessage("Il y a " + str(yesCount) + " oui, " + str(noCount) + " non et " + str(blankCount) + " blancs.")
		
        numberOfVotes = len(self.votingUrn.keys())

        if (numberOfVotes > 0):
            yesPercentage = round(100 * yesCount / numberOfVotes)
            noPercentage = round(100 * noCount / numberOfVotes)
            blankPercentage = round(100 * blankCount / numberOfVotes)
            self.sendMucMessage("Les scores sont de " + str(yesPercentage) + "% pour le oui, " + str(noPercentage) + "% pour le non et " + str(blankPercentage) + "% de vote blancs.")

            winner = None                    
            if (yesPercentage > noPercentage and yesPercentage > blankPercentage):
                winner = 'Oui'
                winnerString = "Le oui l'emporte"
                winnerCount = yesCount
            elif (noPercentage > yesPercentage and noPercentage > blankPercentage):
                winner = 'no'
                winnerString = "Le non l'emporte"
                winnerCount = noCount
            elif (blankPercentage > yesPercentage and blankPercentage > noPercentage):
                winner = 'blank'
                winnerString = "Le blanc l'emporte"
                winnerCount = blankCount

            if winner != None:
                self.sendMucMessage(winnerString)                   
                if (winnerCount >= math.ceil(numberOfVotes/2) + 1):
                    self.sendMucMessage("La majorité absolue est atteinte.")
                else:
                    self.sendMucMessage("La majorité absolue n'est pas atteinte.") 
            else:
                self.sendMucMessage("Egalité.")
        else:
            self.sendMucMessage("Pas de votes.")
                              
    def muc_message(self, msg):
        if msg['mucnick'] != self.nick:
            if not self.referendumStarted:
                if re.search(REFERENDUM_RX, msg['body'].decode('utf8'), re.IGNORECASE | re.UNICODE):             
                    self.referendumOwner = self.plugin['xep_0045'].getJidProperty(self.room, msg['mucnick'], 'jid').bare
                    self.referendumOwnerNick = msg['mucnick']
                    self.referendumStarted = True
                    self.mto = msg['from'].bare
                    print "Referendum started by " + self.referendumOwner
                    self.sendMucMessage(self.referendumOwnerNick + ", pose une question.")
                                      
            elif self.referendumStarted and not self.questionAsked:
                if self.plugin['xep_0045'].getJidProperty(self.room, msg['mucnick'], 'jid').bare == self.referendumOwner:
                    self.sendMucMessage("Vous pouvez maintenant voter pendant " + str(VOTE_DURATION) + " secondes. Oui ou non.")
                    self.question = msg['body']
                    self.questionAsked = True
                    self.startTimer()
                    
            elif self.referendumStarted and self.questionAsked:
                command = None
                
                #Vote
                if re.search(YES_RX, msg['body'].decode('utf8'), re.IGNORECASE | re.UNICODE):
                    command = 'yes'
                if re.search(NO_RX, msg['body'].decode('utf8'), re.IGNORECASE | re.UNICODE):
                    command = 'no'
                if re.search(BLANK_RX, msg['body'].decode('utf8'), re.IGNORECASE | re.UNICODE):
                    command = 'blank'

                if command != None:
                    self.send_message(mto=msg['from'], mbody="Vote de " + self.plugin['xep_0045'].getJidProperty(self.room, msg['mucnick'], 'jid').bare + " enregistré.", mtype='chat') 
                    #self.sendMucMessage()
                    self.votingUrn[self.plugin['xep_0045'].getJidProperty(self.room, msg['mucnick'], 'jid').bare] = command
                
                #Autres commandes
                if re.search(QUESTION_RX, msg['body'].decode('utf8'), re.IGNORECASE | re.UNICODE):
                    self.sendMucMessage(self.question)
                
                if re.search(RESULTAT_RX, msg['body'].decode('utf8'), re.IGNORECASE | re.UNICODE):
                    self.sendResult()
                                          
                    
                        
                    
            
                    

if __name__ == '__main__':
    # Setup the command line arguments.
    optp = OptionParser()

    # Output verbosity options.
    optp.add_option('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-v', '--verbose', help='set logging to COMM',
                    action='store_const', dest='loglevel',
                    const=5, default=logging.INFO)

    # JID and password options.
    optp.add_option("-j", "--jid", dest="jid",
                    help="JID to use")
    optp.add_option("-p", "--password", dest="password",
                    help="password to use")
    optp.add_option("-r", "--room", dest="room",
                    help="MUC room to join")
    optp.add_option("-n", "--nick", dest="nick",
                    help="MUC nickname")

    opts, args = optp.parse_args()

    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')

    if opts.jid is None:
        opts.jid = raw_input("Username: ")
    if opts.password is None:
        opts.password = getpass.getpass("Password: ")
    if opts.room is None:
        opts.room = raw_input("MUC room: ")
    if opts.nick is None:
        opts.nick = raw_input("MUC nickname: ")

    xmpp = MUCBot(opts.jid, opts.password, opts.room, opts.nick)
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0045') # Multi-User Chat
    xmpp.register_plugin('xep_0199') # XMPP Ping

    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")