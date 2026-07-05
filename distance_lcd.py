# Measure distance with an HC-SR04 ultrasonic sensor and show it on an LCD1602.
#
# How the sensor works: it's like a bat. We tell it to send a short burst of
# ultrasonic sound (TRIG pin), it raises its ECHO pin for exactly as long as
# the sound is in flight, and we time that. Sound travels at 340 m/s, so:
#     distance = flight_time * 340 / 2      (divided by 2: there AND back)

import machine
import time
from lcd1602 import LCD1602   # our LCD driver (lcd1602.py on the board)

# --- Pin setup -------------------------------------------------------------

# TRIG is an OUTPUT: we pulse it to say "fire a sound burst now".
TRIG = machine.Pin(17, machine.Pin.OUT)
# ECHO is an INPUT: the sensor raises it while the sound is traveling.
ECHO = machine.Pin(16, machine.Pin.IN)

# The LCD is connected in 4-bit mode on these GPIOs:
#   rs = "register select" (command or character?)
#   e  = "enable", the doorbell pulse that makes the LCD read the data lines
#   d4-d7 = the four data lines (each character is sent as two 4-bit halves)
lcd = LCD1602(rs=2, e=3, d4=4, d5=5, d6=6, d7=7)

# --- Measuring -------------------------------------------------------------

def distance():
    """Fire one ultrasonic ping and return the distance in centimeters.
    Returns None if no echo came back (nothing in range)."""

    # Send a clean 10-microsecond pulse on TRIG. That's the "fire!" signal.
    TRIG.low()
    time.sleep_us(2)
    TRIG.high()
    time.sleep_us(10)
    TRIG.low()

    # Wait for ECHO to go high = the burst has left the sensor.
    # The 30000 us (30 ms) timeout stops us from waiting forever if the
    # sensor never answers - without it the program could freeze here.
    t0 = time.ticks_us()
    while not ECHO.value():
        if time.ticks_diff(time.ticks_us(), t0) > 30000:
            return None

    # ECHO is now high. Note the time, then wait for it to drop low again
    # (= the reflection arrived back). Same timeout idea as above.
    time1 = time.ticks_us()
    while ECHO.value():
        if time.ticks_diff(time.ticks_us(), time1) > 30000:
            return None
    time2 = time.ticks_us()

    # How long was ECHO high, in microseconds?
    # ticks_diff handles the microsecond counter wrapping around.
    during = time.ticks_diff(time2, time1)

    # Convert time to distance:
    #   during [us] * 340 [m/s] / 2  ... then / 10000 turns the units into cm
    return during * 340 / 2 / 10000

# --- Display helpers --------------------------------------------------------

def pad(text, width=16):
    """Stretch text to exactly 16 characters (the LCD row width).
    The added spaces overwrite leftovers from the previous, longer message -
    otherwise '8.2 cm' printed over 'out of range' would show '8.2 cmrange'."""
    return (text + " " * width)[:width]

# --- Main program -----------------------------------------------------------

lcd.clear()
lcd.write_at(0, 0, "Distance:")   # top row, written once - it never changes

while True:                        # repeat forever (this is the whole app)
    dis = distance()

    # The sensor is only reliable up to ~400 cm; beyond that (or when no
    # echo returned at all) we show "out of range" instead of a bogus number.
    if dis is None or dis > 400:
        line = "out of range"
    else:
        line = "%.1f cm" % dis     # format with 1 decimal, e.g. "12.4 cm"

    print("Distance:", line)       # goes to the USB serial port (for the Mac)
    lcd.write_at(0, 1, pad(line))  # bottom row of the LCD

    time.sleep_ms(300)             # ~3 measurements per second
