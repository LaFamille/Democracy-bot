#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import re
import threading
import math

REFERENDUM_RX = u'^r[é|e]f[é|e]rendum\s+[!|.]+'
YES_RX = r'o+u+i+\s*[!|.]*$'
NO_RX = r'n+o+n+\s*[!|.]*$'
BLANK_RX = r'b+l+a+n+c+\s*[!|.]*$'
RESULTAT_RX = u'r[é|e]sultat\s*[!|.]*'
QUESTION_RX = u'question\s*[!|.]*'

VOTE_DURATION = 60

class ReferendumActivity:
    def __init__(self, botInstance):
        self.referendumStarted = False
        self.questionAsked = False
        self.referendumOwner = None
        self.referendumOwnerNick = None
        self.question = ''
        self.votingUrn = dict()
        self.botInstance = botInstance

    def startTimer(self):
        threading.Timer(VOTE_DURATION, self.timerEnd).start() 
        
    def timerEnd(self):
        print "timerEnd"
        self.botInstance.sendMucMessage("Le vote est maintenant terminé.");
        self.botInstance.sendMucMessage("La question était : \"" + self.question + "\"");
        self.sendResult()
        self.referendumStarted = False
        self.questionAsked = False
        self.votingUrn.clear()
        
    def sendResult(self):
        yesCount = sum( vote == 'yes' for vote in self.votingUrn.values() )
        noCount = sum( vote == 'no' for vote in self.votingUrn.values() )
        blankCount = sum( vote == 'blank' for vote in self.votingUrn.values() )
        self.botInstance.sendMucMessage("Il y a " + str(yesCount) + " oui, " + str(noCount) + " non et " + str(blankCount) + " blancs.")
        
        numberOfVotes = len(self.votingUrn.keys())
        
        if (numberOfVotes > 0):
            yesPercentage = round(100 * yesCount / numberOfVotes)
            noPercentage = round(100 * noCount / numberOfVotes)
            blankPercentage = round(100 * blankCount / numberOfVotes)
            self.botInstance.sendMucMessage("Les scores sont de " + str(yesPercentage) + "% pour le oui, " + str(noPercentage) + "% pour le non et " + str(blankPercentage) + "% de vote blancs.")

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
                self.botInstance.sendMucMessage(winnerString)                   
                if (winnerCount >= math.ceil(numberOfVotes/2) + 1):
                    self.botInstance.sendMucMessage("La majorité absolue est atteinte.")
                else:
                    self.botInstance.sendMucMessage("La majorité absolue n'est pas atteinte.") 
            else:
                self.botInstance.sendMucMessage("Egalité.")
        else:
            self.botInstance.sendMucMessage("Pas de votes.")
            
    def private_message(self, msg):
        return
        #senderRealJid = self.plugin['xep_0045'].getJidProperty(self.room, msg['mucnick'], 'jid')
        #print "Private msg - From : " + str(msg['from']) + " type :  " + msg['type'] + " mucnick : " + msg['mucnick']
    
    def muc_message(self, msg):
        senderRealJid = self.botInstance.getRealJidForMucnick(msg['mucnick'])
        print "MUC msg - From : " + str(msg['from']) + " type :  " + msg['type'] + " mucnick : " + msg['mucnick']
        if not self.referendumStarted and senderRealJid != None:
            if re.search(REFERENDUM_RX, msg['body'].decode('utf8'), re.IGNORECASE | re.UNICODE):             
                self.referendumOwner = senderRealJid
                self.referendumOwnerNick = msg['mucnick']
                self.referendumStarted = True
                self.mto = msg['from'].bare
                print "Referendum started by " + self.referendumOwner.bare
                self.botInstance.sendMucMessage(self.referendumOwnerNick + ", pose une question.")
                                  
        elif self.referendumStarted and not self.questionAsked:
            if senderRealJid == self.referendumOwner:
                self.botInstance.sendMucMessage("Vous pouvez maintenant voter pendant " + str(VOTE_DURATION) + " secondes. Oui ou non.")
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

                
            with open("/home/pi/XMPP/blacklist.cfg") as f:
                blacklist = f.readlines()
                
                senderCanVote = True    
                for blacklistedNick in blacklist:
                    splittedJid = senderRealJid.bare.split("@")[0].decode('utf8')
                    if blacklistedNick.rstrip() == splittedJid:
                        senderCanVote = False
                    
            if command != None and senderCanVote:
                self.botInstance.send_message(mto=msg['from'], 
                                  mbody="Vote de " + senderRealJid.bare + " enregistré.", 
                                  mtype='chat') 
                #self.sendMucMessage()
                self.votingUrn[senderRealJid] = command
            
            #Autres commandes
            if re.search(QUESTION_RX, msg['body'].decode('utf8'), re.IGNORECASE | re.UNICODE):
                self.botInstance.sendMucMessage(self.question)
            
            if re.search(RESULTAT_RX, msg['body'].decode('utf8'), re.IGNORECASE | re.UNICODE):
                self.sendResult()
                                      