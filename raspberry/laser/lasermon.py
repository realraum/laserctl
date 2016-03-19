#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
from cardsdb import CardsDB
import rfid
import math
import colorsys
import json
import atexit
try:
    import paho.mqtt.client as mqtt
    usemqtt_ = True
    mqttclient_ = None
    print("MQTT enabled")
except:
    usemqtt_ = False

#BUZZER_PIN = 8
#LASER_PIN = 10
BUZZER_PIN = 14
LASER_PIN = 15
DEADMANBUTTON_GPIO = 25 #PIN22, GPIO25
NUM_WARNINGS_CARD_LOST = 5
DEADMANBUTTON_TIMEOUT_S = 30
LOOP_DELAY_S = 1
LEDS_TEENSY_TTY = "/dev/ttyACM0"
FRACTION_RED = 0.32
MQTT_BROKER_HOST="mqtt.realraum.at"
MQTT_BROKER_PORT=1883

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

    def waitTillCardRemoved(self):
        while rfid.tagIsPresent():
            time.sleep(0.2)

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

    def beepButtonPressNeeded(self):
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.07)
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        time.sleep(0.08)
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        time.sleep(0.07)
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
        usersname = self.myDatabase.get_fullname(self.cardId)
        mqttNotifyLaserHot(True, usersname)
        visualizeLaserHot()
        self.beepShort()
        self.laserOn()

        startTime = time.time()
        endTime = startTime
        self.myDatabase.log_card_activated(self.cardId)
        lostcounter = NUM_WARNINGS_CARD_LOST
        deadmanbutton_timeout_s = DEADMANBUTTON_TIMEOUT_S
        lowest_fraction = 1.0
        buttonPressDeadManSwitchDetected() # simulate Button Press (bad bad without lock... but really better not to use those in python callbacks)
        while True:
            time.sleep(LOOP_DELAY_S)
            fraction_time_remaining_deadmanbutton = 1.0 - (getSecondsSinceLastDeadmanButtonPress()/deadmanbutton_timeout_s)
            lowest_fraction = min(lowest_fraction, fraction_time_remaining_deadmanbutton)
            if lostcounter == NUM_WARNINGS_CARD_LOST:
                visualizeRemainingTimeFraction(fraction_time_remaining_deadmanbutton)
                if fraction_time_remaining_deadmanbutton < FRACTION_RED:
                    self.beepButtonPressNeeded()
            ## Check DeadMan Button
            if getSecondsSinceLastDeadmanButtonPress() > deadmanbutton_timeout_s:
                endTime = time.time()
                break
            ## if someone waits until the last second, he needs to press more often in the future
            if lowest_fraction == fraction_time_remaining_deadmanbutton and lowest_fraction < 0.10:
                deadmanbutton_timeout_s = DEADMANBUTTON_TIMEOUT_S / 2

            ## Check for Card
            cardId = self.checkCard()
            if cardId == self.cardId:
                # if card was lost and now is back, this also counts as button press
                if lostcounter < NUM_WARNINGS_CARD_LOST:
                    buttonPressDeadManSwitchDetected()
                lostcounter = NUM_WARNINGS_CARD_LOST
                continue

            # Card Lost !!
            if lostcounter == NUM_WARNINGS_CARD_LOST:
                endTime = time.time()
                visualizeCardLost()
            if lostcounter > 0:
                lostcounter -= 1
                ## last ditch rescue ability
                if getSecondsSinceLastDeadmanButtonPress() <= NUM_WARNINGS_CARD_LOST:
                    lostcounter = NUM_WARNINGS_CARD_LOST
                    continue
                if lostcounter < NUM_WARNINGS_CARD_LOST /2:
                    self.beepCardLost()
                continue

            # Lost counter == 0
            break
        # switch off laser
        visualizeLaserOff()
        self.beepLong()
        self.laserOff()

        # add minutes to card
        numberSeconds = int(endTime - startTime)
        self.myDatabase.log_card_finished(self.cardId, numberSeconds)
        print("%d: End cardID %d, seconds=%d" % (time.time(), myApp.cardId, numberSeconds))
        mqttNotifyLaserHot(False,usersname)

        # wait until card removed
        self.waitTillCardRemoved()

    def laserOff(self):
        GPIO.output(BUZZER_PIN, GPIO.HIGH)
        GPIO.output(LASER_PIN, GPIO.HIGH)

    def laserOn(self):
        GPIO.output(LASER_PIN, GPIO.LOW)

last_deadmanbutton_press = 0
def buttonPressDeadManSwitchDetected(gpionum=None):
    global last_deadmanbutton_press
    last_deadmanbutton_press = time.time()

def getSecondsSinceLastDeadmanButtonPress():
    global last_deadmanbutton_press
    return time.time() - last_deadmanbutton_press

def hsv(h, s, v):
    return rgb(*colorsys.hsv_to_rgb(h, s, v))

def rgb(r, g, b):
    return "%02X%02X%02X" % (int(r*0xff)&0xff, int(g*0xff)&0xff, int(b*0xff)&0xff)

def visualizeRemainingTimeFraction(fraction):
    if fraction < 0:
        fraction = 0
    try:
        max_brightness = 0.15
        #frame_delay_start = "F01F4" #500ms
        frame_delay_start = "F0078" #1/8s
        if fraction > FRACTION_RED:
            h = 0.3 #green
        else:
            h = 0.045 #red
        num_full = int(8.0 * fraction)
        num_empty = 8 - int(math.ceil(8.0 * fraction))
        num_gray = 8 - num_full - num_empty
        sub_fraction = (8.0 * fraction - num_full)
        assert(sub_fraction <= 1.0)
        v = sub_fraction * max_brightness #max brightness
        with open(LEDS_TEENSY_TTY, "w") as ttyfh:
            ttyfh.write("S04\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+ [hsv(h, 1.0, v)]*num_gray +[hsv(h, 1.0, max_brightness)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+ [hsv(h-0.0095, 1.0, v)]*num_gray +[hsv(h-0.0095, 1.0, max_brightness)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+ [hsv(h-0.008, 1.0, v)]*num_gray +[hsv(h-0.008, 1.0, max_brightness)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+ [hsv(h-0.0058, 1.0, v)]*num_gray +[hsv(h-0.0058, 1.0, max_brightness)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+ [hsv(h-0.003, 1.0, v)]*num_gray +[hsv(h-0.003, 1.0, max_brightness)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+ [hsv(h-0.0058, 1.0, v)]*num_gray +[hsv(h-0.0058, 1.0, max_brightness)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+ [hsv(h-0.008, 1.0, v)]*num_gray +[hsv(h-0.008, 1.0, max_brightness)]*num_full)+"\n")
            ttyfh.write(frame_delay_start+"".join([rgb(0, 0, 0)]*num_empty+ [hsv(h-0.0095, 1.0, v)]*num_gray +[hsv(h-0.0095, 1.0, max_brightness)]*num_full)+"\n")
            ttyfh.write("E\n")
    except Exception as e:
        print(e)

def visualizeLaserHot():
    visualizeSendAnimationFile("white-blink.anim")

def visualizeCardLost():
    visualizeSendAnimationFile("rgb-slow.anim")

def visualizeLaserOff():
    visualizeSendAnimationFile("rgb-fast.anim")

def visualizeStandby():
    visualizeSendAnimationFile("knightrider.anim")

def visualizeSendAnimationFile(fn):
    try:
        with open(fn, "r") as animfh:
            with open(LEDS_TEENSY_TTY, "w") as ttyfh:
                ttyfh.write(animfh.read())
    except Exception as e:
        print(e)

def mqttNotifyLaserHot(ishot, who):
    global mqttclient_
    if usemqtt_ == False:
        return
    try:
        if mqttclient_ is None:
            mqttclient_ = mqtt.Client(client_id="lasercutter")
            mqttclient_.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
            mqttclient_.loop_start()
            atexit.register(mqttclient_.loop_stop)
        mqttclient_.publish("realraum/lasercutter/cardpresent", payload=json.dumps({"IsHot":ishot,"Who":who,"Ts":int(time.time())}), qos=0, retain=True)
    except Exception as e:
        print("MQTT Error:", e)

if __name__ == '__main__':

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(BUZZER_PIN, GPIO.OUT)
    GPIO.setup(LASER_PIN, GPIO.OUT)
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    GPIO.output(LASER_PIN, GPIO.HIGH)
    GPIO.setup(DEADMANBUTTON_GPIO, GPIO.IN, GPIO.PUD_UP)
    GPIO.add_event_detect(DEADMANBUTTON_GPIO, GPIO.BOTH, buttonPressDeadManSwitchDetected, 100) #100ms debounce

    myApp = LaserMon()
    while True:
        visualizeStandby()
        myApp.cardId = myApp.readCard()
        if myApp.cardId >= 0:
            print("%d: Run cardID %d" % (time.time(), myApp.cardId))
            myApp.continueLaser = True
            myApp.run()

