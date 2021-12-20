# ---------------------------------Import necessary libraries and modules ----------------------------------------------
import RPi.GPIO as GPIO
import time
from Adafruit_LED_Backpack import SevenSegment
# This is library import for max7219 compatibility
from luma.led_matrix.device import max7219
# SPI communication
from luma.core.interface.serial import spi, noop
# Import canvas
from luma.core.render import canvas
from luma.core.legacy.font import TINY_FONT
from luma.core.legacy import show_message

# -------------------------- Initialisation of led matrix device and interface -----------------------------------------
# Define the serial interface (SPI)
serial = spi(port=0, device=1, gpio=noop())
# Defining a max7219 device
device = max7219(serial, cascaded=1, block_orientation=90, rotate=0)

# Define a segment object
SSD = SevenSegment.SevenSegment(address=0x70)
# Initialise the 7SD
SSD.begin()

# ----------------- Initialisation of the variables along with GPIO pins and the ultrasonic sensor ---------------------
bar_height = [9 for h in range(8)]
update_rate = 1
archive = [0 for i in range(100)]
calibre = [0 for j in range(10)]
exact_bar_height = [0 for m in range(8)]
alpha = 10360

# Define GPIO numbering mode
GPIO.setmode(GPIO.BCM)
PinUp = 26
PinLeft = 25
PinRight = 19
PinDown = 13
PinVibration = 27
functional_buttons = [PinUp, PinLeft, PinRight, PinDown]
# Define pins of Trigger and Echo pin
PinTrigger = 16
PinEcho = 12
GPIO.setup(functional_buttons, GPIO.IN)
GPIO.setup(PinVibration, GPIO.OUT)
# Define Trigger pin as output
GPIO.setup(PinTrigger, GPIO.OUT)
# Define Echo pin as input
GPIO.setup(PinEcho, GPIO.IN)
# Set Trigger pin to false and wait for 1 sec.
GPIO.output(PinTrigger, False)
print('Initialising Sensor')
time.sleep(1)

# --------------------------------- Defining functions used in the program ---------------------------------------------


def ultrasonic(trigger, echo):
    # Set Trigger for 1ms to TRUE and reset afterwards
    print('Sending Trigger signal')
    GPIO.output(trigger, True)
    time.sleep(0.00001)
    GPIO.output(trigger, False)
    # Measure t1 as long as echo pin is FALSE
    while GPIO.input(echo) == 0:
        pulse_start = time.time()
    # Measure t2 as long as echo pin is TRUE
    while GPIO.input(echo) == 1:
        pulse_end = time.time()
    # Calculate pulse duration
    pulse_duration = pulse_end - pulse_start
    # Calculate distance and show it in the console
    distance = pulse_duration * 17241
    print("Distance:", distance, "cm")
    return pulse_duration


def seven_segment(duration, alpha_factor=10360):
    duration_percent = duration * alpha_factor
    str_duration_percent = str(round(duration_percent, 1))
    SSD.set_digit(0, 0)
    SSD.set_digit(1, 0)
    SSD.print_number_str(str_duration_percent)
    # Write character
    SSD.write_display()
    SSD.clear()
    return duration_percent


def led_matrix(height_bar):
    with canvas(device) as draw:
        for i in range(0, 8):
            draw.point([i, 7 - height_bar[i]], fill="white")

# --------------------------------- Defining additional functionality functions ----------------------------------------


def paused_mode(pin_left):
    global left_button_status
    left_button_status = 0


def active_mode(pin_left):
    global left_button_status
    left_button_status = 1


def refresh_rate(pin_up):
    global update_rate
    update_rate = update_rate + 1
    if update_rate == 10:
        update_rate = 1
    print("The update rate has been changed to:", update_rate)


def navigation_function(pin_right):
    global navigate_position
    print("navigate position", navigate_position)
    print("passed on bar height", manual_bar_height)
    seven_segment(archive[navigate_position], alpha)

    if navigate_position == 0:
        led_matrix(manual_bar_height)

    elif 0 < navigate_position < 93:
        duration_percent = archive[navigate_position + 7] * alpha
        point_location = int(round(7 * (duration_percent / 100)))

        for i in range(len(manual_bar_height) - 1):
            manual_bar_height[7 - i] = manual_bar_height[6 - i]
        manual_bar_height[0] = point_location
        print(manual_bar_height)
        led_matrix(manual_bar_height)

    elif 92 < navigate_position < 100:
        for i in range(len(manual_bar_height) - (8-100+navigate_position)):
            manual_bar_height[8 - i] = manual_bar_height[7 - i]
        for j in range(8-100+navigate_position):
            manual_bar_height[j] = 9
        led_matrix(manual_bar_height)

    elif navigate_position == 100:
        print("Reached the end of the archive storage")
        navigate_position = -1

    navigate_position = navigate_position + 1


def calibration(pin_down):
    GPIO.output(PinVibration, GPIO.HIGH)
    total = 0.0
    global alpha
    print("Calibration process has been started....")
    for i in range(10):
        print("Finding ultrasonic sensor measured value", i+1)
        measurement = ultrasonic(PinTrigger, PinEcho)
        calibre[i] = measurement
        time.sleep(0.5)
    for j in range(len(calibre)):
        total = total + calibre[j]
    alpha = total / 10
    alpha = 100 / alpha
    GPIO.output(PinVibration, GPIO.LOW)
    print("Updated scaling factor is", alpha)


def direct_access(pin_up):
    a = int(input("Please enter the archive address position number to be accessed\t"))
    if 0 <= a < 92:
        duration_percent = seven_segment(archive[a], alpha)
        point_location = int(round(7 * (duration_percent / 100)))
        for j in range(7):
            temp = archive[a+j+1] * alpha
            temp = int(round(7 * (temp / 100)))
            exact_bar_height[6-j] = temp
        exact_bar_height[7] = point_location
        led_matrix(exact_bar_height)
    elif 91 < a < 100:
        seven_segment(archive[a], alpha)
        for j in range(8):
            temp = archive[92+j] * alpha
            temp = int(round(7 * (temp / 100)))
            exact_bar_height[7-j] = temp
        exact_bar_height[7] = exact_bar_height[100-a]
        for y in range(100-a):
            exact_bar_height[7-y] = exact_bar_height[7-y-(8-100+a)]
        for x in range(8-100+a):
            exact_bar_height[x] = 9
        led_matrix(exact_bar_height)
    else:
        print("Address not in the range of the archive size."
              "\nTo access the required location please press the top navigation button again.")
    print("The percentage duartion of the accessed location", a, "is", duration_percent)


# --------------------------------------------------  Main Code --------------------------------------------------------

while True:
    left_button_status = 1
    print("System is online")
    while left_button_status:
        actual_duration = ultrasonic(PinTrigger, PinEcho)
        for i in range(99):
            archive[99 - i] = archive[98 - i]
        archive[0] = actual_duration

        percent_duration = seven_segment(actual_duration, alpha)
        height = int(round(7 * (percent_duration / 100)))

        for i in range(len(bar_height) - 1):
            bar_height[i] = bar_height[i + 1]
        bar_height[7] = height
        led_matrix(bar_height)

        if not 'rate' in locals():
            rate = GPIO.add_event_detect(PinUp, GPIO.FALLING, callback=refresh_rate, bouncetime=200)
        # Waiting time between two measurements
        time.sleep(update_rate)

        if not 'pause' in locals():
            pause = GPIO.add_event_detect(PinLeft, GPIO.FALLING, callback=paused_mode, bouncetime=200)

    manual_bar_height = bar_height.copy()
    GPIO.remove_event_detect(PinUp)
    GPIO.remove_event_detect(PinLeft)
    del rate, pause

    print("System is in paused mode")
    print("Latest three archive contents", archive[:3])
    navigate_position = 0
    show_message(device, "System is in paused mode!",
                 fill="white", font=TINY_FONT, scroll_delay=0.07)
    while not left_button_status:
        if not 'active' in locals():
            active = GPIO.add_event_detect(PinLeft, GPIO.FALLING, callback=active_mode, bouncetime=200)

        if not 'navigate' in locals():
            navigate = GPIO.add_event_detect(PinRight, GPIO.FALLING, callback=navigation_function, bouncetime=200)

        if not 'recalibrate' in locals():
            recalibrate = GPIO.add_event_detect(PinDown, GPIO.FALLING, callback=calibration, bouncetime=300)

        if not 'access' in locals():
            access = GPIO.add_event_detect(PinUp, GPIO.FALLING, callback=direct_access, bouncetime=200)

    GPIO.remove_event_detect(PinRight)
    GPIO.remove_event_detect(PinLeft)
    GPIO.remove_event_detect(PinDown)
    GPIO.remove_event_detect(PinUp)
    del active, navigate, recalibrate, access
