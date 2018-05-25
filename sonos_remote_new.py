'''
Based on the @loboris ESP32 MicroPython port
Uses the m5stack dev board with wrover with 4mb psram
Uses some m5stack helper scripts from:
tuupola @ https://github.com/tuupola/micropython-m5stack

Left(A) button lowers volume, Right(C) raises, Middle(B) is play_pause
Publishes these actions to to topic sonos/{loc} using AWS mqtt broker and
a local raspberry pi script esp_check_mqtt3.py is subscribed to that topic
and executes the appropriate action

Also displays track information that is being published
by local raspberry pi script sonos_track_info3.py to the
same AWS EC2 mqtt broker by subscribing to sonos/{loc}/track

Displays images of the artists that have been placed on sdcard
Laptop script url_image2sdcard.py is used to create the images
in a local directory that are then copied to the sdcard
'''
#import gc # not sure if needed
import network
from time import sleep, time, strftime, localtime #sleep_ms
import json
from config import mqtt_aws_host
from settings import ssid, pw, mqtt_id, location as loc
import m5stack # m5stack imports input; from tuupola @ https://github.com/tuupola/micropython-m5stack

sub_topic = 'sonos/{}/track'.format(loc)
pub_topic =  'sonos/{}'.format(loc)
flag = bytearray(1)

print("mqtt_id =", mqtt_id)
print("host =", mqtt_aws_host)
print("subscribe topic =", sub_topic)
print("publish topic =", pub_topic)

#i2c = I2C(scl=Pin(22), sda=Pin(23)) #speed=100000 is the default

tft = m5stack.Display()
tft.font(tft.FONT_DejaVu18, fixedwidth=False)
tft.clear()
tft.text(tft.CENTER, 20, "Hello Steve \n")

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

def datacb(msg):
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

# decrease the volume
def button_hander_a(pin, pressed):
  if pressed:
    flag[0] = 1

# play/pause
def button_hander_b(pin, pressed):
  if pressed:
    flag[0] = 2

# increase the volume
def button_hander_c(pin, pressed):
  if pressed:
    flag[0] = 3

a = m5stack.ButtonA(callback=button_hander_a)
b = m5stack.ButtonB(callback=button_hander_b)
c = m5stack.ButtonC(callback=button_hander_c)

actions = {1:'quieter', 2:'play_pause', 3:'louder'}
cur_time = 0

while 1:
  t = time()
  if t > cur_time + 600:
    print(strftime("%c", localtime()))
    cur_time = t
  #gc.collect()
  if flag[0]:
    try:
      mqttc.publish(pub_topic, json.dumps({'action':actions[flag[0]]}))
    except Exception as e:
      print(e)
    print(actions[flag[0]])
    m5stack.tone(1800, duration=10, volume=1)
    flag[0] = 0
  sleep(.1)
