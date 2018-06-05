'''
Based on the @loboris ESP32 MicroPython port
Uses the m5stack dev board with wrover with 4mb psram
Combines the original sonos_remote concept of a
left button lowers volume, right raises, middle is play_pause
To also include the m5sonos_menu concept that allows more actions
to be taken than just volume and play/pause.
Also displays track information that is being published by local raspsberry pii
sonos-companion script esp_check_mqtt4.py to AWS EC2 mqtt broker

Actions are published to topic: sonos/ct or sonos/nyc
The topic that is subscribed to for track info is sonos/{loc}/track
'''
#import gc # not sure if needed
from time import sleep, time, strftime, localtime #time, sleep_ms, strftime, localtime
#from machine import RTC #Pin, I2C
import m5stack # from tuupola @ https://github.com/tuupola/micropython-m5stack

import network
import json
from config import mqtt_aws_host
#from settings import mqtt_id #location as loc
from settings import mqtt_id, location as loc

# the below is where I'd like things to go with main writing to
# the file location
#with open('location', 'r') as f:
#    loc = f.read()

sub_topic = 'sonos/{}/track'.format(loc)
pub_topic =  'sonos/{}'.format(loc)
flag = bytearray(1)

print("mqtt_id =", mqtt_id)
print("host =", mqtt_aws_host)
print("subscribe topic =", sub_topic)
print("publish topic =", pub_topic)

actions = {0:"play_pause",
           1:"quieter",
           2:"louder",
           3:"station wnyc",
           4:"station patty griffin",
           5:"shuffle neil young",
           6:"shuffle jason isbell",
           7:"shuffle patty griffin"}

#page = 1 #0 = artist picture and track info; 1 = menu items, 2 = more menu items etc.
n = 10

def draw_menu():
    global row
    global page
    page = 1
    row = 10
    tft = m5stack.Display()
    tft.font(tft.FONT_DejaVu18, fixedwidth=False)
    tft.clear()
    for i,action in actions.items():
        tft.text(20, n+i*25, action)

    tft.text(5, 10, ">")

def wrap(text,lim):
  lines = []
  pos = 0 
  line = []
  for word in text.split():
    if pos + len(word) < lim + 1:
      line.append(word)
      pos+= len(word) + 1 
    else:
      lines.append(' '.join(line))
      line = [word] 
      pos = len(word)

  lines.append(' '.join(line))
  return lines

def conncb(task):
  print("[{}] Connected".format(task))

#def disconncb(task):
#  print("[{}] Disconnected".format(task))

def subscb(task):
  print("[{}] Subscribed".format(task))

# for some reason this callback seems to cause a Guru Meditation Error
def pubcb(pub):
  print("[{}] Published: {}".format(pub[0], pub[1]))

def datacb___(msg):
  print("[{}] Data arrived - topic: {}, message:{}".format(msg[0], msg[1], msg[2]))

  try:
    zz = json.loads(msg[2])
  except Exception as e:
    print(e)
    zz = {}

  artist = zz.get('artist', '')
  title = zz.get('title', '')
  y = n+8*25
  s = "{}-{}".format(artist, title)[:30]
  tft.textClear(5, y, "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx") 
  tft.text(5, y, s, tft.CYAN)

def datacb(msg):
  global page
  global row
  page = 0
  row = 10
  print("[{}] Data arrived - topic: {}, message:{}".format(msg[0], msg[1], msg[2]))

  try:
    zz = json.loads(msg[2])
  except Exception as e:
    print(e)
    zz = {}

  tft.clear()
  artist = zz.get('artist', '')
  if artist:
    try:
      tft.image(0,0,'/sd/{}.jpg'.format(artist.lower().replace(' ', '_')))
    except:
      pass
  tft.text(5, 5, artist+"\n") 

  title = wrap(zz.get('title', ''), 28) # 28 seems right for DejaVu18
  for line in title:
    tft.text(5, tft.LASTY, line+"\n")

# note published callback doesn't seem to do anything
mqttc = network.mqtt(mqtt_id, mqtt_aws_host, connected_cb=conncb,
                     cleansession=True, subscribed_cb=subscb,
                     published_cb=pubcb, data_cb=datacb, clientid=mqtt_id)

mqttc.start()
sleep(1)

mqttc.subscribe(sub_topic)

# ButtonA
def button_hander_a(pin, pressed):
  global row
  if pressed:
    print("A pressed")
    if page:
      tft.text(5, row, "  ")
      row+=25
      tft.text(5, row, ">")
      #print("action number =", (row-n)//25)
      m5stack.tone(1800, duration=10, volume=1)
    else:
      draw_menu()

# ButtonB
def button_hander_b(pin, pressed):
  global flag
  if pressed:
    flag = 1
    print("B pressed")
    #print("action number =", (row-n)//25)
    m5stack.tone(1800, duration=10, volume=1)

# ButtonC
def button_hander_c(pin, pressed):
  global row
  if pressed:
    print("C pressed")
    if page:
      tft.text(5, row, "  ")
      row-=25
      tft.text(5, row, ">")
      #print("action number =", (row-n)//25)
      m5stack.tone(1800, duration=10, volume=1)
    else:
      draw_menu()

a = m5stack.ButtonA(callback=button_hander_a)
b = m5stack.ButtonB(callback=button_hander_b)
c = m5stack.ButtonC(callback=button_hander_c)

draw_menu()

cur_time = 0
while 1:
  t = time()
  if t > cur_time + 600:
    print(strftime("%c", localtime()))
    cur_time = t
  #gc.collect()
  if flag:
    print("action number =", (row-n)//25)
    try:
      mqttc.publish(pub_topic, json.dumps({'action':actions[(row-n)/25]}))
    except Exception as e:
      print(e)
    flag = 0
  sleep(.1)
