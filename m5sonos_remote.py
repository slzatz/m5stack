'''
Based on the @loboris ESP32 MicroPython port
Uses the m5stack dev board with wrover with 4mb psram
The evolution of the sonos_remote concept
When image (chapter = 0) is showing:
left button lowers volume, right raises volume, middle displays menu (chapter=1)
The m5sonos_menu concept enable multiple chapters and pages of menus
Also displays an image and track information that is being published by
a local raspberry pi to the aws mosquitto broker
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
from settings import mqtt_id, uris

# main.py writes the file location on reset
with open('location', 'r') as f:
    loc = f.read()

sub_topic = 'sonos/{}/track'.format(loc)
#pub_topic =  'sonos/{}'.format(loc)
#flag = bytearray(1)
flag = 0
page = 0
chapter = 1
_N = const(5)
uri = uris[loc]
track_info = {}
row = _N

print("mqtt_id =", mqtt_id)
print("host =", mqtt_aws_host)
print("subscribe topic =", sub_topic)
print("uri = ", uri)
#print("publish topic =", pub_topic)

#each list corresponds to a chapter
#chapter 4, the queue, gets filled in programmatically

actions = [
[("","quieter"), ("","louder")],

[  ("play/pause","play_pause"),
   ("quieter","quieter"),
   ("louder","louder"),
   ("skip","next"),
   ("WNYC","station wnyc"),
   ("Pandora mix","station quickmix"),
   ("shuffle ...","shuffle"), # 2 shuffle> def display_choices()
   ("Pandora station ...","station"), #3
   ("show queue ...","queue"),
   ("mute", "mute"),
   ("unmute", "unmute")],

# the shuffle menu that follows is now read from a file
[],

[  ("WNYC","station wnyc"),
   ("Patty Griffin","station patty griffin"),
   ("Neil Young","station neil young"),
   ("Pandora mix", "station quickmix"),
   ("R.E.M","station rem"),
   ("Lucinda Williams","station lucinda william"),
   ("Counting Crows","station counting crows"),
   ("Dar Williams","station dar williams")],

[]
]

# get artists for shuffle menu
try:
    response = urequests.post(uri, json={'action':'list_artists'})
    q = response.json()
except Exception as e:
    q = ["There was a problem"]
    print("error =", e)
response.close()
actions[2] = q 


tft = m5stack.Display()
tft.font(tft.FONT_DejaVu18, fixedwidth=False)

def draw_menu():
    tft.clear()
    a_page = actions[chapter][page*9:page*9+9]
    for i,action in enumerate(a_page):
        tft.text(20, _N+i*25, action[0])

    tft.text(5, row, ">")

def display_image():
  tft.clear()
  artist = track_info.get('artist', '')
  if artist:
    try:
      #tft.image(0,0,'/sd/{}.jpg'.format(artist.lower().replace(' ', '_')))
      tft.image(0,0,'/sd/{}.jpg'.format(artist.lower()))
    except Exception as e:
      print("display_image: ",e)
      pass
  tft.text(5, 5, artist+"\n") 

  title = wrap(track_info.get('title', ''), 28) # 28 seems right for DejaVu18
  for line in title:
    tft.text(5, tft.LASTY, line+"\n")

def display_queue(new=True): 
    if new:
        try:
            response = urequests.post(uri, json={'action':'list_queue'})
            q = response.json()
        except Exception as e:
            q = ["There was a problem"]
            print("error list_queue =", e)
        response.close()
        actions[4] = q 
    try:
        response = urequests.post(uri, json={'action':'track_pos'})
        pos = int(response.text) - 1
        print("pos =",pos)
    except Exception as e:
        pos = -1
        print("error track_pos =", e)
    response.close()
    actions[4] = q 
    tft.clear()
    page_actions = actions[4][page*9:page*9+9]
    for i,track in enumerate(page_actions):
        if page*9 + i == pos:
            tft.text(20, _N+i*25, track, tft.RED)
        else:
            tft.text(20, _N+i*25, track)
    tft.text(5, row, '>')

def display_artists():
    tft.clear()
    page_actions = actions[2][page*9:page*9+9]
    for i,artist in enumerate(page_actions):
        tft.text(20, _N+i*25, artist)
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

def datacb(msg):
    global chapter
    global row
    global page
    chapter = 0
    row = _N
    print("[{}] Data arrived - topic: {}, message:{}".format(msg[0], msg[1], msg[2]))

    try:
        z = json.loads(msg[2])
    except Exception as e:
        print(e)
        z = {}

    track_info.update(z)
    chapter = page = 0
    display_image()

# note published callback doesn't seem to do anything
mqttc = network.mqtt(mqtt_id, 'mqtt://'+mqtt_aws_host, connected_cb=conncb,
                     cleansession=False, subscribed_cb=subscb,
                     published_cb=pubcb, data_cb=datacb, clientid=mqtt_id)

mqttc.start()
sleep(1)

mqttc.subscribe(sub_topic)

# ButtonA
def button_hander_a(pin, pressed):
    global flag
    global row
    global page
    if pressed:
        print("A pressed")
        if chapter:
            tft.text(5, row, "  ")
            if row == 205: #> 200:
                page+=1
                row = _N
                if chapter < 4:
                    draw_menu()
                else:
                    display_queue(new=False)
            else:
                row+=25
                tft.text(5, row, ">")

        else:
            #if image showing -> quieter
            row = _N + 25
            flag = 1

        m5stack.tone(1800, duration=10, volume=1)

# ButtonB
def button_hander_b(pin, pressed):
    global flag
    global page
    global chapter
    if pressed:
        print("B pressed")
        print("chapter =", chapter)
        if chapter:
            flag = 1
        else:
            page = 0
            chapter = 1
            draw_menu()  

        m5stack.tone(1800, duration=10, volume=1)

# ButtonC
def button_hander_c(pin, pressed):
    global flag
    global row
    global page
    if pressed:
        print("C pressed")
        if chapter:
            tft.text(5, row, "  ")
            if row == 5: #< 6: #probably = 5 better
                page-=1
                row = 205
                if chapter < 4:
                    draw_menu()
                else:
                    display_queue(new=False)
            else:
                row-=25
                tft.text(5, row, ">")

        else:
            #if image showing -> louder
            row = _N + 50
            flag = 1

        m5stack.tone(1800, duration=10, volume=1)

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
    if flag:
        action_num = page*9 + (row-_N)//25
        print("action number =", action_num)
        if chapter < 2:
            action = actions[1][action_num][1]
            try:
                idx = ['shuffle','station','queue'].index(action)
            except ValueError:
                pass
            else:
                row = _N
                if idx==0:
                    chapter=2
                    page=0
                    display_artists()
                elif idx==2:
                    chapter=4
                    page=0
                    display_queue(new=True)
                else:
                    chapter = idx+2
                    page = 0
                    draw_menu()

                flag = 0
                print("action =", action)
                continue #######################################
            #print("action =", action)

        elif chapter == 2:
            action = "shuffle "+actions[2][action_num]
            
        elif chapter == 3:
            action = "station "+actions[2][action_num]

        elif chapter == 4:
            action = "play_queue "+str(action_num)

        print("action =", action)

        try:
            response = urequests.post(uri, json={'action':action})
            response.close()
        except Exception as e:
            print("error =", e)

        flag = 0
        if chapter: # chapter could equal zero if this was volume on image
            chapter = page = 0
            display_image()
    #gc.collect()
    sleep(.1)
