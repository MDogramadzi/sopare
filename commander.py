import pexpect
import time, threading
from threading import Thread
import json
import os
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(4,GPIO.OUT)
GPIO.setup(17,GPIO.OUT)


# Read in the mapping file for IR commands to Trained words
ir_map = {}

with open('ir_map.json') as f:
    ir_map = json.load(f)


# Bluetooth Setup Stages

bluetooth_child = pexpect.spawn("sudo node bluetooth_server.js", timeout=None)


bluetooth_child.expect("on -> servicesSet: success")
print("Bluetooth Server Active")
# activate an LED showing that device is on
GPIO.output(4,GPIO.HIGH)


bluetooth_child.expect('on -> accept, client:.*')
print("Device Connected")
# activate an LED showing Bluetooth connection is active

speechRecogniserActive = False


def runListener(speech_child):
    while True:
        if speechRecogniserActive:
            speech_child.expect('\[.*\]')
            handleRecognisedWord(speech_child.after)
        else:
            return


def handleRecognisedWord(word):
    # emit IR code, activate 'ready' mode
    print(word)
    for label, trainedArray in ir_map.items():
        if word == str(trainedArray):
            print("Emitting: ", label)
            command = "irsend SEND_ONCE marko " + label
            os.system(command)



def checkStopListening(bluetooth_child):
    global speechRecogniserActive
    bluetooth_child.expect('Writing: stop listening')
    print("Kill process: sopare.py -l")
    speechRecogniserActive = False


def blinkLED():
    GPIO.output(17,GPIO.HIGH)
    time.sleep(0.2)
    GPIO.output(17,GPIO.LOW)


try:
    while True:
        # ["Writing: start listening", "Writing: train-power", ...]
        i = bluetooth_child.expect(['Writing: start listening', 'Writing: train-.*', 'Writing: record-.*', "Writing: update-.*"])
        if i == 0:

            speechRecogniserActive = True
            print("Spawn process: sopare.py -l")
            speech_child = pexpect.spawn("./sopare.py -l", timeout=None)

            process = Thread(target=runListener, args=[speech_child])
            process.start()
            GPIO.output(17,GPIO.HIGH)

            bluetooth_child.expect('Writing: stop listening')
            print("Kill process: sopare.py -l")
            speechRecogniserActive = False
            GPIO.output(17,GPIO.LOW)
            speech_child.kill(0)
            speech_child.close()

        elif i == 1:
            input = bluetooth_child.after
            trainingWord = input.split("-")[1]
            print("Training word: " + trainingWord)
            train_proc = "./sopare.py -v -t " + trainingWord
            training_child = pexpect.spawn(train_proc)
            training_child.expect("INFO:sopare.buffering:buffering queue runner")
            blinkLED()
            print("Training Ready")
            training_child.expect("INFO:sopare.recorder:stop endless recording")
            blinkLED()
            time.sleep(0.2)
            blinkLED()
            print("Training Complete")
            training_child.close()
            os.system("./sopare.py -c")
            print("Compiled and added new word")

        elif i == 2:
            input = bluetooth_child.after
            ir_label = input.split("-")[1]
            print("Recording with IR Label: " + ir_label)
            os.system("sudo /etc/init.d/lircd stop")
            time.sleep(2)
            record_child = pexpect.spawn("irrecord --disable-namespace -u /etc/lirc/lircd.conf.d/marko.lircd.conf")
            time.sleep(2)
            record_child.sendline()
            time.sleep(2)
            record_child.sendline(ir_label)
            record_child.expect("Please enter the name for the next button.*")
            blinkedLED()
            print("Ready for IR command")
            record_child.expect("Please enter the name for the next button.*")
            record_child.sendline()
            os.system("sudo /etc/init.d/lircd start")
            print("Command Addition Complete")
            ir_map_cur = {}
            with open("ir_map.json", "r") as f:
                ir_map_cur = json.load(f)
            ir_map_cur[ir_label.rstrip('\r\n').decode('utf8')] = []
            with open("ir_map.json", "w") as f:
                json.dump(ir_map_cur, f)
            blinkLED()
            time.sleep(0.2)
            blinkLED()


        elif i == 3:
            input = bluetooth_child.after
            commandLabel = input.split("-")[1].split("|")[0]
            triggerList = input.split("-")[1].split("|")[1]
            triggerList = map(str.strip, triggerList.split("/"))
            triggerList = [item.decode('utf8') for item in triggerList]
            print("Updating IR code with Label: " + commandLabel)
            print("Trigger List Array is: ", triggerList)
            ir_map_cur = {}
            with open("ir_map.json", "r") as f:
                ir_map_cur = json.load(f)
            ir_map_cur[commandLabel] = triggerList
            with open("ir_map.json", "w") as f:
                json.dump(ir_map_cur, f)
            print("Updating mapping file with new triggers")


        else:
            print("Unknown command")

except KeyboardInterrupt:
    print("Interrupt: Exiting Program")

finally:
    GPIO.cleanup()

