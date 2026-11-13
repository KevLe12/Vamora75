"""Vamora75 boot.py - hold Esc while plugging in for the writable CIRCUITPY drive + serial REPL."""
import time
import digitalio
import microcontroller
import storage
import usb_cdc
import usb_hid
import usb_midi

ESC_COL, ESC_ROW = microcontroller.pin.GPIO29, microcontroller.pin.GPIO0
c = digitalio.DigitalInOut(ESC_COL)
r = digitalio.DigitalInOut(ESC_ROW)
r.switch_to_input(pull=digitalio.Pull.DOWN)
c.switch_to_output(value=True)
time.sleep(0.01)
maintenance = r.value
c.deinit()
r.deinit()
usb_midi.disable()
if not maintenance:
    storage.disable_usb_drive()
    usb_cdc.disable()
usb_hid.set_interface_name("Vamora75")
usb_hid.enable((usb_hid.Device.KEYBOARD, usb_hid.Device.CONSUMER_CONTROL), boot_device=0 if maintenance else 1)
