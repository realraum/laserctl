import RPi.GPIO as GPIO
import time, threading
from cardsdb import CardsDB
import rfid

#BUZZER_PIN = 8
#LASER_PIN = 10
BUZZER_PIN = 14
LASER_PIN = 15

#----------------------------------------------------------------------------
#
# Lasermon
# - init 
#   switch off relais and beeper
# - if card with units detected -> open relais, start timer
# - timer timeout -> if card is not detected within 15 secs -> switch off, else restart timer
# - every minute -> decrease units of card
#
#----------------------------------------------------------------------------
class LaserMon():
    def __init__(self):
        self.myDatabase = CardsDB()
        self.numberMinutes = 0
        self.continueLaser = False
        self.cardId = -1;

    def readCard(self):
        while True:
            rfid.waitTag()
            if rfid.readMifare():
                uid = rfid.getUniqueId()
                id = self.myDatabase.cardExists(uid)
                if id >= 0:
                    #print ("READ: Card found")
                    return id
                else:
                    #print ("READ: Card NOT found")
                    return -1
                break
            else:
                return -1

    def checkCard(self):
        if rfid.tagIsPresent():
            if rfid.readMifare():
                uid = rfid.getUniqueId()
                id = self.myDatabase.cardExists(uid)
                if id >= 0:
                    #print ("CHECK: Card found")
                    return id
                else:
                    #print ("CHECK: Card NOT found")
                    return -1
            else:
                return -1
        else:
            return -1


    def beepShort(self):
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(BUZZER_PIN, GPIO.HIGH)

    #  wait for a card to read
    #  if card -> start laser, init countr
    #  wait 1 Minute 
    #  set alarm
    #  
    #  
    def run(self):

        secondsRunning = 60
        secondsWarning = 10

        self.laserOn()

        continueLaser = True 
        while continueLaser == True:
            startTime = time.time()
            finishTime = startTime + secondsRunning

            while time.time() < finishTime:
                time.sleep(1)

            self.beepShort()

            self.numberMinutes += 1

            counter = 0
            while counter < secondsWarning:
                cardId = self.checkCard()
                if cardId == self.cardId:
                    break
                counter = counter+1
                time.sleep(0.5)
                self.beepShort()
            else:
                continueLaser = False 

        # switch off laser
        self.laserOff()

        # add minutes to card
        self.myDatabase.update_units(self.cardId,self.numberMinutes)

    def laserOff(self):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        GPIO.output(LASER_PIN, GPIO.HIGH)

    def laserOn(self):
        GPIO.output(LASER_PIN, GPIO.LOW)

if __name__ == '__main__':

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.setup(LASER_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    GPIO.output(LASER_PIN, GPIO.HIGH)

    myApp = LaserMon()
    while 1:
        myApp.cardId = myApp.readCard()
        if ( myApp.cardId >= 0 ):
            print("Run cardID %d" % myApp.cardId)
            myApp.continueLaser = True
            myApp.numberMinutes = 0
            myApp.run()

