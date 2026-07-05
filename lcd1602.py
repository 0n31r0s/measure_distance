# Driver for the LCD1602 character display, wired directly to GPIO pins
# ("4-bit parallel mode" - no I2C adapter board).
#
# The LCD has a tiny controller chip (HD44780) that understands two kinds
# of bytes: COMMANDS (clear screen, move cursor, ...) and CHARACTERS to
# display. Three control ideas cover everything this file does:
#
#   RS pin  - "register select": tells the LCD whether the data lines hold
#             a command (RS=0) or a character (RS=1)
#   E pin   - "enable": the doorbell. The LCD reads the data lines at the
#             moment E pulses high->low. No pulse, no message.
#   D4-D7   - four data lines. A byte has 8 bits, so we send it in two
#             halves ("nibbles"): upper 4 bits first, then lower 4 bits.
#             Half the wires of full 8-bit mode, same result, just 2 sends.

import machine
import utime

class LCD1602:
    def __init__(self, rs, e, d4, d5, d6, d7):
        # Every pin is an OUTPUT: we only talk TO the display
        # (its RW pin is wired to GND = permanently "write mode").
        self.rs = machine.Pin(rs, machine.Pin.OUT)
        self.e = machine.Pin(e, machine.Pin.OUT)
        self.data_pins = [
            machine.Pin(d4, machine.Pin.OUT),
            machine.Pin(d5, machine.Pin.OUT),
            machine.Pin(d6, machine.Pin.OUT),
            machine.Pin(d7, machine.Pin.OUT),
        ]
        self._init_lcd()

    def _pulse_enable(self):
        """Ring the doorbell: a short high pulse on E makes the LCD
        read whatever is currently on the data lines."""
        self.e.value(0)
        utime.sleep_us(1)
        self.e.value(1)
        utime.sleep_us(1)      # datasheet: E must stay high >= 450 ns
        self.e.value(0)
        utime.sleep_us(40)     # give the LCD time to process what it read

    def _send_nibble(self, nibble):
        """Put 4 bits on the data lines, then pulse E."""
        for i in range(4):
            # (nibble >> i) & 1 picks out bit number i (0 or 1)
            self.data_pins[i].value((nibble >> i) & 1)
        self._pulse_enable()

    def _send_byte(self, byte, mode):
        """Send a full byte as two nibbles. mode = 0 command, 1 character."""
        self.rs.value(mode)         # set RS *before* pulsing E
        self._send_nibble(byte >> 4)      # upper half first...
        self._send_nibble(byte & 0x0F)    # ...then lower half

    def command(self, cmd):
        """Send a command byte (RS=0), e.g. 'clear' or 'move cursor'."""
        self._send_byte(cmd, 0)
        utime.sleep_ms(2)      # commands need a little longer than characters

    def write_char(self, char):
        """Send one visible character (RS=1). ord() = its character code."""
        self._send_byte(ord(char), 1)
        utime.sleep_us(50)

    def _init_lcd(self):
        """The wake-up ritual from the HD44780 datasheet. Fresh from power-on
        the LCD assumes 8-bit mode; this exact sequence of magic nibbles and
        pauses switches it into 4-bit mode so our two-halves trick works.
        (Skip or garble this and you get the famous 'row of dark blocks'.)"""
        utime.sleep_ms(500)    # let the LCD's own power-on reset finish
        self.rs.value(0)
        self.e.value(0)
        # Say "8-bit mode" three times - this resets it to a known state
        # no matter what confused state it was in before.
        self._send_nibble(0x03)
        utime.sleep_ms(5)
        self._send_nibble(0x03)
        utime.sleep_ms(1)
        self._send_nibble(0x03)
        utime.sleep_us(150)
        self._send_nibble(0x02)  # NOW switch to 4-bit mode
        # From here on, normal two-nibble commands work:
        self.command(0x28)  # function set: 4-bit bus, 2 lines, 5x8 pixel font
        self.command(0x0C)  # display on, cursor off, blinking off
        self.clear()
        self.command(0x06)  # entry mode: cursor moves right after each char

    def clear(self):
        """Wipe the screen and put the cursor at the top-left."""
        self.command(0x01)
        utime.sleep_ms(2)   # clear is the slowest command the LCD has

    def set_cursor(self, col, row):
        """Move the cursor. The LCD's memory maps row 0 to address 0x00
        and row 1 to address 0x40; 0x80 marks the byte as a 'move' command."""
        addr = col + (0x40 if row == 1 else 0x00)
        self.command(0x80 | addr)

    def write(self, text):
        """Print a string at the current cursor position."""
        for char in text:
            self.write_char(char)

    def write_at(self, col, row, text):
        """Move the cursor, then print - the usual one-call convenience."""
        self.set_cursor(col, row)
        self.write(text)
