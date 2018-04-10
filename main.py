# Boris main.py
import machine
import network
import utime
from settings import ssid, pw

print("")
print("Starting WiFi ...")

sta_if = network.WLAN(network.STA_IF)

_ = sta_if.active(True)
_ = sta_if.connect(ssid, pw)

tmo = 50
while not sta_if.isconnected():
    utime.sleep_ms(100)
    tmo -= 1
    if tmo == 0:
        break

if tmo > 0:
    ifcfg = sta_if.ifconfig()
    print("WiFi started, IP:", ifcfg[0])
    utime.sleep_ms(500)

    rtc = machine.RTC()
    print("Synchronize time from NTP server ...")
    rtc.ntp_sync(server="hr.pool.ntp.org", tz="EST5EDT") # update once
    #rtc.ntp_sync(server="hr.pool.ntp.org", update_period=3600)
    tmo = 100
    while not rtc.synced():
        utime.sleep_ms(100)
        tmo -= 1
        if tmo == 0:
            break

    if tmo > 0:
        utime.sleep_ms(200)
        print("Time set:", utime.strftime("%c"))
        print("")
        _ = network.ftp.start()
        _ = network.telnet.start()
        try:
            mdns = network.mDNS()
            _ = mdns.start("mPy","MicroPython with mDNS")
            _ = mdns.addService('_ftp', '_tcp', 21, "MicroPython", {"board": "ESP32", "service": "mPy FTP File transfer", "passive": "True"})
            _ = mdns.addService('_telnet', '_tcp', 23, "MicroPython", {"board": "ESP32", "service": "mPy Telnet REPL"})
            _ = mdns.addService('_http', '_tcp', 80, "MicroPython", {"board": "ESP32", "service": "mPy Web server"})
        except:
            print("mDNS not available")

def reset():
    machine.reset()

import sonos_remote_m5stack

