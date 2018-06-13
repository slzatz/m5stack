'''
Based on the @loboris ESP32 MicroPython port
Uses the m5stack dev board with wrover with 4mb psram
Combines the original sonos_remote concept of a
When image (page = 0) is showing:
left button lowers volume, right raises volume, middle displays menu (page=1)
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
import urequests
from config import mqtt_aws_host
from settings import mqtt_id 
#from settings import mqtt_id, location as loc

# main.py writes the file location on reset
with open('location', 'r') as f:
    loc = f.read()

sub_topic = 'sonos/{}/track'.format(loc)
pub_topic =  'sonos/{}'.format(loc)
flag = bytearray(1)
uri = 'http://192.168.1.126:5000/actions'

print("mqtt_id =", mqtt_id)
print("host =", mqtt_aws_host)
print("subscribe topic =", sub_topic)
print("publish topic =", pub_topic)

actions = [
['quieter', 'louder'],

[  "play_pause",
   "quieter",
   "louder",
   "next",
   "station wnyc",
   "station quickmix",
   "shuffle menu 2",
   "station menu 3",
   "queue"],

[  "shuffle neil young",
   "shuffle jason isbell",
   "shuffle patty griffin",
   "shuffle israel nash",
   "shuffle gillian welch",
   "shuffle counting crows",
   "shuffle courtney barnett",
   "shuffle dar williams"],

[  "station wnyc",
   "station patty griffin",
   "station neil young",
   "station quickmix",
   "station rem",
   "station lucinda william",
   "station counting crows",
   "station dar williams"],

[]
]   



# this becomes combo of row (which it is now) and page so 1:0 is play_pause and 2:0 is ...
#page = 1 #0 = artist picture and track info; 1 = menu items, 2 = more menu items etc.
# or page is sub-page

tft = m5stack.Display()
tft.font(tft.FONT_DejaVu18, fixedwidth=False)

_N = const(5)
track_info = {}

def draw_menu(p):
    global row
    global page
    page = p
    row = _N
    tft.clear()
    #for i,action in new_actions[p].items():
    for i,action in enumerate(actions[p]):
        tft.text(20, _N+i*25, action)

    tft.text(5, row, ">")

def display_queue(q):
    global row
    global page
    page = 4
    row = _N
    tft.clear()
    print("q =",q)
    for i,track in enumerate(q):
        tft.text(20, _N+i*25, track)
    tft.text(5, row, '>')

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

def display_image():

  tft.clear()
  artist = track_info.get('artist', '')
  if artist:
    try:
      tft.image(0,0,'/sd/{}.jpg'.format(artist.lower().replace(' ', '_')))
    except:
      pass
  tft.text(5, 5, artist+"\n") 

  title = wrap(track_info.get('title', ''), 28) # 28 seems right for DejaVu18
  for line in title:
    tft.text(5, tft.LASTY, line+"\n")

def datacb(msg):
  global page
  global row
  #global track_info
  #track_info = msg
  page = 0
  row = _N
  print("[{}] Data arrived - topic: {}, message:{}".format(msg[0], msg[1], msg[2]))

  try:
    z = json.loads(msg[2])
  except Exception as e:
    print(e)
    z = {}

  track_info.update(z)
  display_image()

# note published callback doesn't seem to do anything
mqttc = network.mqtt(mqtt_id, mqtt_aws_host, connected_cb=conncb,
                     cleansession=True, subscribed_cb=subscb,
                     published_cb=pubcb, data_cb=datacb, clientid=mqtt_id)

mqttc.start()
sleep(1)

mqttc.subscribe(sub_topic)

# ButtonA
def button_hander_a(pin, pressed):
  global flag
  global row
  if pressed:
    print("A pressed")
    if page:
      tft.text(5, row, "  ")
      row+=25
      tft.text(5, row, ">")
    else:
      #if image showing -> quieter
      row = _N 
      flag = 1

    m5stack.tone(1800, duration=10, volume=1)

# ButtonB
def button_hander_b(pin, pressed):
  global flag
  if pressed:
    print("B pressed")
    if page:
      flag = 1
    else:
      draw_menu(1)  

    m5stack.tone(1800, duration=10, volume=1)

# ButtonC
def button_hander_c(pin, pressed):
  global flag
  global row
  if pressed:
    print("C pressed")
    if page:
      tft.text(5, row, "  ")
      row-=25
      tft.text(5, row, ">")
      m5stack.tone(1800, duration=10, volume=1)
    else:
      #if image showing -> louder
      row = _N + 25
      flag = 1

    m5stack.tone(1800, duration=10, volume=1)

a = m5stack.ButtonA(callback=button_hander_a)
b = m5stack.ButtonB(callback=button_hander_b)
c = m5stack.ButtonC(callback=button_hander_c)

draw_menu(1)

cur_time = 0
while 1:
  t = time()
  if t > cur_time + 600:
    print(strftime("%c", localtime()))
    cur_time = t
  #gc.collect()
  #if page == 1: xxxx
  #if flag == 
  if flag:
    action_num = (row-_N)//25
    print("action number =", action_num)
    action = actions[page][action_num]
    print("action =", action)
    if 'menu' in action:
      draw_menu(int(action[-1]))
      flag = 0
      continue
    elif action == 'queue':
      response = urequests.post(uri, json={'action':'list_queue'})
      queue = response.json()
      actions[4] = queue
      display_queue(queue)
      flag = 0
      continue
    try:
      mqttc.publish(pub_topic, json.dumps({'action':action}))
    except Exception as e:
      print(e)
    flag = 0
    if page: # page could equal zero if this was volume on image
      page = 0
      display_image()
  sleep(.1)
