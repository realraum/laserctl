import RPi.GPIO as GPIO
import time
from cardsdb import CardsDB
import rfid
import math
import colorsys

#BUZZER_PIN = 8
#LASER_PIN = 10
BUZZER_PIN = 14
LASER_PIN = 15
DEADMANBUTTON_GPIO = 24 #PIN8, GPIO24
NUM_WARNINGS = 5
DEADMANBUTTON_TIMEOUT_S = 30
LOOP_DELAY_S = 1
LEDS_TEENSY_TTY = "/dev/ttyACM0"

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
        self.cardId = -1

    def readCard(self):
        while True:
            rfid.waitTag()
            if rfid.readMifare():
                uid = rfid.getUniqueId()
                cid = self.myDatabase.cardExists(uid)
                if cid >= 0:
                    #print ("READ: Card found")
                    self.beepShort()
                    return cid
                else:
                    #print ("READ: Card NOT found")
                    self.beepLong()
                    return -1
                break
            else:
                return -1

    def checkCard(self):
        if rfid.tagIsPresent():
            if rfid.readMifare():
                uid = rfid.getUniqueId()
                cid = self.myDatabase.cardExists(uid)
                if cid >= 0:
                    #print ("CHECK: Card found")
                    return cid
                else:
                    #print ("CHECK: Card NOT found")
                    return -1
            else:
                return -1
        else:
            return -1

    def beepCardLost(self):
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(0.02)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.05)
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(0.02)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.2)
        GPIO.output(BUZZER_PIN, GPIO.HIGH)

    def beepShort(self):
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.08)
        GPIO.output(BUZZER_PIN, GPIO.HIGH)

    def beepLong(self):
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(1.5)
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

        self.beepShort()
        self.laserOn()

        startTime = time.time()
        lostcounter = NUM_WARNINGS
        deadmanbutton_timeout_s = DEADMANBUTTON_TIMEOUT_S
        lowest_fraction = 1.0
        buttonPressDeadManSwitchDetected() # simulate Button Press (bad bad without lock... but really better not to use those in python callbacks)
        while True:
            time.sleep(LOOP_DELAY_S)
            fraction_time_remaining_deadmanbutton = 1.0 - (getSecondsSinceLastDeadmanButtonPress()/deadmanbutton_timeout_s)
            lowest_fraction = min(lowest_fraction, fraction_time_remaining_deadmanbutton)
            visualizeRemainingTimeFraction(fraction_time_remaining_deadmanbutton)
            ## Check DeadMan Button
            if getSecondsSinceLastDeadmanButtonPress() > deadmanbutton_timeout_s:
                break
            ## if someone waits until the last second, he needs to press more often in the future
            if lowest_fraction == fraction_time_remaining_deadmanbutton and lowest_fraction < 0.05:
                deadmanbutton_timeout_s = DEADMANBUTTON_TIMEOUT_S / 2

            ## Check for Card
            cardId = self.checkCard()
            if cardId == self.cardId:
                lostcounter = NUM_WARNINGS
                continue

            # Card Lost !!
            if lostcounter == NUM_WARNINGS:
                endTime = time.time()
            if lostcounter > 0:
                lostcounter -= 1
                ## last ditch rescue ability
                if getSecondsSinceLastDeadmanButtonPress() <= NUM_WARNINGS - lostcounter:
                    lostcounter = NUM_WARNINGS
                    continue
                self.beepCardLost()
                continue

            # Lost counter == 0
            break
        # switch off laser
        self.beepLong()
        self.laserOff()

        # add minutes to card
        numberMinutes = int(math.ceil((endTime - startTime)/60.0))
        self.myDatabase.update_units(self.cardId, numberMinutes)
        print("End cardID %d, minutes=%d" % (myApp.cardId, numberMinutes))

    def laserOff(self):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        GPIO.output(LASER_PIN, GPIO.HIGH)
        visualizeLaserOff()

    def laserOn(self):
        visualizeLaserHot()
        GPIO.output(LASER_PIN, GPIO.LOW)

last_deadmanbutton_press = 0
def buttonPressDeadManSwitchDetected():
    global last_deadmanbutton_press
    last_deadmanbutton_press = time.time()

def getSecondsSinceLastDeadmanButtonPress():
    global last_deadmanbutton_press
    return time.time() - last_deadmanbutton_press

def hsv(h, s, v):
    return rgb(*colorsys.hsv_to_rgb(h, s, v))

def rgb(r, g, b):
    return "%X%X%X" % (int(r*0xff)&0xff, int(g*0xff)&0xff, int(b*0xff)&0xff)

def visualizeRemainingTimeFraction(fraction):
    try:
        frame_delay_start = "F0030"
        h = 0.3 + (1.0 - fraction) * 0.7 # start in green, go to red
        v = 0.8 - fraction * 0.8 #max brightness
        with open(LEDS_TEENSY_TTY, "w") as ttyfh:
            ttyfh.write("S04\n")
            num_full = int(math.ceil(8.0 * fraction))
            num_empty = 8 - num_full
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+[hsv(h, 1.0, v)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+[hsv(h, 1.0, v+0.03)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+[hsv(h, 1.0, v+0.08)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+[hsv(h, 1.0, v+0.03)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+[hsv(h, 1.0, v)]*num_full)+"\n")
            ttyfh.write("E\n")
    except Exception as e:
        print(e)

def visualizeLaserHot():
    visualizeSendAnimationFile("white-blink.anim")

def visualizeLaserOff():
    visualizeSendAnimationFile("rgb-slow.anim")

def visualizeStandby():
    visualizeSendAnimationFile("knightrider.anim")

def visualizeSendAnimationFile(fn):
    try:
        with open(fn, "r") as animfh:
            with open(LEDS_TEENSY_TTY, "w") as ttyfh:
                ttyfh.write(animfh.read())
    except Exception as e:
        print(e)

if __name__ == '__main__':

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.setup(LASER_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    GPIO.output(LASER_PIN, GPIO.HIGH)
    GPIO.setup(DEADMANBUTTON_GPIO, GPIO.INPUT, GPIO.PUD_UP)
    GPIO.add_event_detect(DEADMANBUTTON_GPIO, GPIO.BOTH, buttonPressDeadManSwitchDetected, 90) #90ms debounce

    myApp = LaserMon()
    while True:
        visualizeStandby()
        myApp.cardId = myApp.readCard()
        if myApp.cardId >= 0:
            print("Run cardID %d" % myApp.cardId)
            myApp.continueLaser = True
            myApp.numberMinutes = 0
            myApp.run()

