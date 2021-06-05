from dmx import Colour, DMXInterface, DMXLight3Slot, DMXLightUking, DMXUniverse
from time import sleep
from sys import exit as sys_exit
import pyaudio
import time
import audioop
import numpy as np
import random

RED = Colour(255,0,0)
GREEN = Colour(0,255,0)
BLUE = Colour(0,0,255)

# create some global constants
SAMPLE_RATE = 44100
BUFFER_SIZE = 4

def decode(in_data, channels):
    '''
    convert a byte stream into a 2D numpy array with 
    shape (chunk_size, channels)

    Samples are interleaved, so for a stereo stream with left channel 
    of [L0, L1, L2, ...] and right channel of [R0, R1, R2, ...], the output 
    is ordered as [L0, R0, L1, R1, ...]
    '''
    # convert between pyaudio/numpy types
    result = np.fromstring(in_data, dtype=np.float32)
    chunk_length = len(result) / channels
    assert chunk_length == int(chunk_length)

    return np.reshape(result, (int(chunk_length), int(channels)))

###########################################################################
def encode(signal):
    """
    Convert a 2D numpy array into a byte stream for PyAudio

    Signal should be a numpy array with shape (chunk_size, channels)
    """
    interleaved = signal.flatten()
    # convert between pyaudio/numpy types
    out_data = interleaved.astype(np.float32).tostring()
    return out_data

##############################################################################
def get_rms():
    # Creates a generator that can iterate rms values
    WIDTH = 2
    CHANNELS = 2
    
    p = pyaudio.PyAudio()

    try:
        stream = p.open(format=p.get_format_from_width(WIDTH),
                        channels=CHANNELS,
                        rate=SAMPLE_RATE,
                        input=True,
                        output=False,
                        frames_per_buffer=BUFFER_SIZE)
        # wait a second to allow the stream to be setup
        time.sleep(1)
        while True:
            # read the data
            data = stream.read(BUFFER_SIZE, exception_on_overflow = False)
            
            # split into left and right channels
            result = decode(data, CHANNELS)
            left = encode(result[:, 0])
            right = encode(result[:, 1])
  
            L_rms = audioop.rms(left, WIDTH)
            R_rms = audioop.rms(right, WIDTH)

            
            # Scale the rms value to be within 0-255
            L_rms_scaled = int((L_rms / 8192) * 255)
            R_rms_scaled = int((R_rms / 8192) * 255)
            if L_rms_scaled <= 255 and L_rms_scaled >= 0 and R_rms_scaled <= 255 and R_rms_scaled >= 0:
                yield L_rms_scaled, R_rms_scaled
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
def create_rms_colour(rms_one, rms_two):
    rms_three = abs(rms_one - rms_two)
    RMS_LIST = [rms_one, rms_two, rms_three]
    r_1 = random.randint(0,2)
    r_2 = random.randint(0,2)
    r_3 = random.randint(0,2)
    return_colour = Colour(RMS_LIST[r_1],
                           RMS_LIST[r_1],
                           RMS_LIST[r_1])
    return(return_colour)

##############################################################################
def main():
    # create an instance of the RMS generator
    audio_feed = get_rms()

    #setup random
    random.seed(500)

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
       
        colour = Colour(0,0,0)
        for L_rms, R_rms in audio_feed:
            D_rms = int((L_rms + R_rms) * 0.5)
            rms_colours = [Colour(L_rms,R_rms,D_rms), Colour(R_rms,L_rms,D_rms), Colour(D_rms,R_rms,L_rms)]
            # if no audio keep updating the colour
            if L_rms <= 10 and R_rms <= 10:
                colour = random.choice(rms_colours)

            light.set_brightness(255)
            light.set_colour(colour)

            light_two.set_colour(colour)
            light_two.set_brightness(255)
            # set frame and update
            set_and_update(universe, interface)
            #sleep(0.5 - (15.0 / 1000.0))
        
        light.set_brightness(0)
        light_two.set_brightness(0)
        set_and_update(universe, interface)
        return 0

if __name__ == '__main__':
    sys_exit(main())
