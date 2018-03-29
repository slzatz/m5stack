# This file is executed on every boot (including wake-boot from deepsleep)
import sys
import uos
sys.path[1] = '/flash/lib'

# the line below works for m5stack using spi
uos.sdconfig(uos.SDMODE_SPI, clk=18, mosi=23, miso=19, cs=4)
uos.mountsd()
