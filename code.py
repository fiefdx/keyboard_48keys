import os
import gc
import time
import analogio
import board
import digitalio
import pwmio
import usb_hid
machine = None
microcontroller = None
try:
    import machine
except:
    try:
        import microcontroller
    except:
        print("no machine & microcontroller module support")
thread = None
try:
    import _thread as thread
except:
    print("no multi-threading module support")

from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode as K
from adafruit_hid.mouse import Mouse
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode as C

from scheduler import Scheluder, Condition, Task, Message
from common import ticks_ms, ticks_add, ticks_diff, sleep_ms

cpu_freq = 120000000
if machine:
    machine.freq(cpu_freq)
    print("freq: %s mhz" % (machine.freq() / 1000000))
if microcontroller:
    microcontroller.cpu.frequency = cpu_freq
    print("freq: %s mhz" % (microcontroller.cpu.frequency / 1000000))


FN = "FN"


def setup_pin(pin, direction, pull = None):
    io = digitalio.DigitalInOut(pin)
    io.direction = direction
    if pull is not None:
        io.pull = pull
    return io


led = setup_pin(board.GP25, digitalio.Direction.OUTPUT) # breathing light for status checking


class CustomKeyBoard(object):
    def __init__(self):
        self.light = 10
        self.light_min = 0
        self.light_max = 100
        time.sleep(1)
        self.mouse = Mouse(usb_hid.devices)
        self.keyboard = Keyboard(usb_hid.devices)
        self.keyboard_layout = KeyboardLayoutUS(self.keyboard)
        self.consumer_control = ConsumerControl(usb_hid.devices)
        self.x_lines = [
            setup_pin(board.GP2, digitalio.Direction.OUTPUT),  # 0
            setup_pin(board.GP3, digitalio.Direction.OUTPUT),  # 1
            setup_pin(board.GP4, digitalio.Direction.OUTPUT),  # 2
            setup_pin(board.GP5, digitalio.Direction.OUTPUT),  # 3
            setup_pin(board.GP6, digitalio.Direction.OUTPUT),  # 4
            setup_pin(board.GP7, digitalio.Direction.OUTPUT),  # 5
            setup_pin(board.GP8, digitalio.Direction.OUTPUT),  # 6
            setup_pin(board.GP9, digitalio.Direction.OUTPUT),  # 7
            setup_pin(board.GP10, digitalio.Direction.OUTPUT), # 8
            setup_pin(board.GP11, digitalio.Direction.OUTPUT), # 9
            setup_pin(board.GP12, digitalio.Direction.OUTPUT), # 10
            setup_pin(board.GP13, digitalio.Direction.OUTPUT), # 11
        ]
        self.y_lines = [
            setup_pin(board.GP14, digitalio.Direction.INPUT, digitalio.Pull.UP), # 0
            setup_pin(board.GP15, digitalio.Direction.INPUT, digitalio.Pull.UP), # 1
            setup_pin(board.GP26, digitalio.Direction.INPUT, digitalio.Pull.UP), # 2
            setup_pin(board.GP27, digitalio.Direction.INPUT, digitalio.Pull.UP), # 3
        ]
        self.keys = [
            [(K.ESCAPE, K.GRAVE_ACCENT), (K.Q, K.ONE), (K.W, K.TWO), (K.E, K.THREE), (K.R, K.FOUR), (K.T, K.FIVE), (K.Y, K.SIX), (K.U, K.SEVEN), (K.I, K.EIGHT), (K.O, K.NINE), (K.P, K.ZERO), (K.BACKSPACE, K.PRINT_SCREEN)],
            [K.TAB, K.A, K.S, (K.D, K.MINUS), (K.F, K.EQUALS), (K.G, K.LEFT_BRACKET), (K.H, K.RIGHT_BRACKET), (K.J, K.QUOTE), (K.K, K.BACKSLASH), K.L, K.SEMICOLON, K.ENTER],
            [K.LEFT_SHIFT, (K.Z, K.F1), (K.X, K.F2), (K.C, K.F3), (K.V, K.F4), (K.B, K.F5), (K.N, K.F6), (K.M, K.F7), (K.COMMA, K.F8), (K.PERIOD, K.F9), (K.FORWARD_SLASH, K.F10), K.RIGHT_SHIFT],
            [K.WINDOWS, (K.DELETE, K.CAPS_LOCK), K.HOME, K.END, K.ALT, FN, K.SPACE, K.LEFT_CONTROL, K.UP_ARROW, K.DOWN_ARROW, (K.LEFT_ARROW, K.PAGE_UP), (K.RIGHT_ARROW, K.PAGE_DOWN)],

            # [K.Q, K.W, K.E, K.R, K.T, K.Y, K.U, K.I, K.O, K.P],
            # [K.A, K.S, K.D, K.F, K.G, K.H, K.J, K.K, K.L, K.SEMICOLON],
            # [K.Z, K.X, K.C, K.V, K.B, K.N, K.M, K.COMMA, K.PERIOD, K.FORWARD_SLASH],
            # [K.ESCAPE, K.QUOTE, K.MINUS, K.EQUALS, K.SPACE, K.ENTER, K.LEFT_BRACKET, K.RIGHT_BRACKET, K.BACKSLASH, (K.BACKSPACE, K.PRINT_SCREEN)],
            # [(K.ONE, K.F1), (K.TWO, K.F2), (K.THREE, K.F3), (K.FOUR, K.F4), (K.FIVE, K.F5), (K.SIX, K.F6), (K.SEVEN, K.DELETE), (K.EIGHT, K.CAPS_LOCK), (K.NINE, K.HOME), (K.ZERO, K.END)],
            # [FN, K.TAB, K.LEFT_CONTROL, K.ALT, K.RIGHT_SHIFT, K.GRAVE_ACCENT, K.UP_ARROW, K.DOWN_ARROW, (K.LEFT_ARROW, K.PAGE_UP), (K.RIGHT_ARROW, K.PAGE_DOWN)],
            #[K.LEFT_SHIFT, (K.F1, K.F7), (K.F2, K.F8), (K.F3, K.F9), (K.F4, K.F10), (K.F5, K.F11), (K.F6, K.F12), (K.HOME, K.END), (K.CAPS_LOCK, K.DELETE), K.RIGHT_SHIFT], K.PAGE_UP, K.PAGE_DOWN
            #[FN, K.WINDOWS ,K.TAB, K.LEFT_CONTROL, K.ALT, K.GRAVE_ACCENT, K.UP_ARROW, K.DOWN_ARROW, K.LEFT_ARROW, K.RIGHT_ARROW],
            # [K.LEFT_SHIFT, K.TAB, K.LEFT_CONTROL, K.ALT, K.GRAVE_ACCENT, K.UP_ARROW, K.DOWN_ARROW, (K.LEFT_ARROW, K.PAGE_UP), (K.RIGHT_ARROW, K.PAGE_DOWN), K.RIGHT_SHIFT],
            # [FN, K.WINDOWS, (K.F1, K.F7), (K.F2, K.F8), (K.F3, K.F9), (K.F4, K.F10), (K.F5, K.F11), (K.F6, K.F12), (K.HOME, K.END), (K.DELETE, K.CAPS_LOCK)],
        ]
        self.press_buttons = [
            [False, False, False, False, False, False, False, False, False, False, False, False],
            [False, False, False, False, False, False, False, False, False, False, False, False],
            [False, False, False, False, False, False, False, False, False, False, False, False],
            [False, False, False, False, False, False, False, False, False, False, False, False],
        ]
        self.buttons = []
        self.release = []

    def press_keys(self, keys = []):
        self.buttons = []
        self.keyboard.press(*keys)
        self.keyboard.release(*keys)
        self.release.clear()

    def scan(self):
        for x in range(12):
            for i in range(12):
                if i == x:
                    self.x_lines[i].value = False # scan x line
                else:
                    self.x_lines[i].value = True # disable other lines
            for y in range(3, -1, -1):
                if self.y_lines[y].value == False: # pressd
                    if self.press_buttons[y][x]: # y,x pressed, already pressed
                        pass
                    else: # y,x not pressed, first press
                        if self.press_buttons[3][5]: # fn pressed
                            if y == 3 and x == 5:
                                pass
                            else:
                                if isinstance(self.keys[y][x], tuple):
                                    self.buttons.append(self.keys[y][x][1])
                                else:
                                    self.buttons.append(self.keys[y][x])
                        else:
                            if y == 3 and x == 5:
                                pass
                            else:
                                if isinstance(self.keys[y][x], tuple):
                                    self.buttons.append(self.keys[y][x][0])
                                else:
                                    self.buttons.append(self.keys[y][x])
                        self.press_buttons[y][x] = True
                else: # not press
                    if self.press_buttons[y][x]:
                        self.press_buttons[y][x] = False
                        if y == 3 and x == 5:
                            pass
                        else:
                            if isinstance(self.keys[y][x], tuple):
                                if self.keys[y][x][0] in self.buttons:
                                    self.buttons.remove(self.keys[y][x][0])
                                    self.release.append(self.keys[y][x][0])
                                else:
                                    self.buttons.remove(self.keys[y][x][1])
                                    self.release.append(self.keys[y][x][1])
                            else:
                                if self.keys[y][x] in self.buttons:
                                    self.buttons.remove(self.keys[y][x])
                                self.release.append(self.keys[y][x])
        if self.press_buttons[3][5]:
            if K.UP_ARROW in self.buttons:
                self.consumer_control.send(C.VOLUME_INCREMENT)
                self.buttons.remove(K.UP_ARROW)
            elif K.DOWN_ARROW in self.buttons:
                self.consumer_control.send(C.VOLUME_DECREMENT)
                self.buttons.remove(K.DOWN_ARROW)
        try:
            self.keyboard.press(*self.buttons)
            self.keyboard.release(*self.release)
            self.release.clear() # = []
        except Exception as e:
            self.release.clear()
            print(e)
            try:
                self.mouse.release_all()
                self.keyboard.release_all()
            except Exception as e:
                print("release_all keys error: ", e)
            try:
                time.sleep(1)
                self.mouse = Mouse(usb_hid.devices)
                self.keyboard = Keyboard(usb_hid.devices)
            except Exception as e:
                print("reinit mouse & keyboard error: ", e)


def monitor(task, name, scheduler = None, display_id = None):
    while True:
        gc.collect()
        monitor_msg = "CPU%s:%3d%%  RAM:%3d%%" % (scheduler.cpu, int(100 - scheduler.idle), int(100 - (scheduler.mem_free() * 100 / (264 * 1024))))
        yield Condition(sleep = 2000, send_msgs = [Message({"msg": monitor_msg}, receiver = display_id)])


def display(task, name):
    while True:
        yield Condition(sleep = 0, wait_msg = True)
        msg = task.get_message()
        print(msg.content["msg"])


def keyboard_scan(task, name, interval = 25, display_id = None):
    k = CustomKeyBoard()
    while True:
        t = ticks_ms()
        try:
            k.scan()
        except Exception as e:
            print(e)
        tt = ticks_ms()
        sleep_time = interval - ticks_diff(tt, t)
        if sleep_time > 0:
            yield Condition(sleep = sleep_time)
        else:
            yield Condition(sleep = 0)


def led_breath(task, name, interval = 500, display_id = None):
    led.value = True
    yield Condition(sleep = interval)
    while True:
        led.value = not led.value
        yield Condition(sleep = interval)


if __name__ == "__main__":
    try:
        s = Scheluder(cpu = 0)
        display_id = s.add_task(Task(display, "display"))
        monitor_id = s.add_task(Task(monitor, "monitor", kwargs = {"scheduler": s, "display_id": display_id}))
        keyboard_id = s.add_task(Task(keyboard_scan, "keyboard", kwargs = {"interval": 50, "display_id": display_id}))
        led_id = s.add_task(Task(led_breath, "led", kwargs = {"interval": 500, "display_id": display_id}))
        s.run()
    except Exception as e:
        print("main: %s" % str(e))
