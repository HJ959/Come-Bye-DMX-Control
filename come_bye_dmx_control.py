from dmx import Colour, DMXInterface, DMXLight3Slot, DMXLightUking, DMXUniverse
from time import sleep
from sys import exit as sys_exit
import pyaudio
import time
import audioop
import numpy as np

RED = Colour(255,0,0)
GREEN = Colour(0,255,0)
BLUE = Colour(0,0,255)



fc = 0.1  # Cutoff frequency as a fraction of the sampling rate (in (0, 0.5)).
b = 0.08  # Transition band, as a fraction of the sampling rate (in (0, 0.5)).
N = int(np.ceil((4 / b)))
if not N % 2: N += 1  # Make sure that N is odd.
n = np.arange(N)
 
# Compute sinc filter.
h = np.sinc(2 * fc * (n - (N - 1) / 2))
 
# Compute Blackman window.
w = 0.42 - 0.5 * np.cos(2 * np.pi * n / (N - 1)) + \
    0.08 * np.cos(4 * np.pi * n / (N - 1))
 
# Multiply sinc filter by window.
h = h * w
 
# Normalize to get unity gain.
h = h / np.sum(h)


###########################################################################
def get_rms():
    # Creates a generator that can iterate rms values
    CHUNK = 8
    WIDTH = 2
    CHANNELS = 1
    RATE = 44100
    
    p = pyaudio.PyAudio()

    
    try:
        stream = p.open(format=p.get_format_from_width(WIDTH),
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        output=False,
                        frames_per_buffer=CHUNK)
        # wait a second to allow the stream to be setup
        time.sleep(1)
        while True:
            # read the data
            data = stream.read(CHUNK, exception_on_overflow = False)
            # apply low pass filter
            rms = audioop.rms(data, 1)
            # Scale the rms value to be within 0-255
            rms_scaled = (rms / 1024) * 255
            if rms_scaled <= 255 and rms_scaled >= 0:
                yield rms_scaled
    finally:
        p.terminate()
        stream.stop_stream()
        stream.close()

##############################################################################
def set_and_update(universe, interface):
    # update the interface's frame to be the universe's current state
    interface.set_frame(universe.serialise())
    # send and update to the DMX network
    interface.send_update()

##############################################################################
def main():
    # create an instance of the RMS generator
    audio_feed = get_rms()

    # Open an interface
    with DMXInterface("FT232R") as interface:
        # create a universe
        universe = DMXUniverse()

        # define a light
        light = DMXLightUking(address=1)
        light_two = DMXLightUking(address=8)

        # Add the light to a universe
        universe.add_light(light)
        universe.add_light(light_two)

        # Set light to purple
        light.set_brightness(0)
        light_two.set_brightness(0)
        set_and_update(universe, interface)
        
        'create a reset light'
        seq_one = [RED, GREEN, BLUE, RED, RED]
        seq_two = [GREEN, BLUE, RED, BLUE, BLUE]


        for rms in audio_feed:  
            light.set_brightness(rms)
            light.set_colour(GREEN)
            light_two.set_colour(BLUE)
            light_two.set_brightness(rms)
            # set frame and update
            set_and_update(universe, interface)
            #sleep(0.5 - (15.0 / 1000.0))
        
        light.set_brightness(0)
        light_two.set_brightness(0)
        set_and_update(universe, interface)
        return 0

if __name__ == '__main__':
    sys_exit(main())
