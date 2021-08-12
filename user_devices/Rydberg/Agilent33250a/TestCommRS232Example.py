"""
TO MAKE THIS FUNCTIONAL:
Put a *FEMALE* DB9 to USB connector into the AWG. Other cable types do not seem to work natively
In Utility on the AWG, ensure the IO setting is for RS232 and all the other settings match with what's in the code below.
"""

import visa
import pyvisa
from pyvisa.constants import StopBits, Parity
import time


def DC(inst, V):
    """ set output to DC mode at voltage V """

    inst.write("APPL:DC DEF,DEF, %.4f" % V)
    inst.write("OUTP OFF")

def gated_sine(inst, Vamp, Voff, freq):
    # break up command total so that AWG doesn't complain about overloaded buffer

    # command_strings = []
    # command_strings.append(r':FUNC SIN')
    # command_strings.append(r':VOLT %.4f V' % Vamp)  # Vpp
    # command_strings.append(r':FREQ %.4f' % freq)  # Hz
    # command_strings.append(r':VOLT:OFFS %.4f V' % Voff)
    # command_strings.append(r':TRIG:SOUR EXT')
    # command_strings.append(r':TRIG:DEL MIN')
    # command_strings.append(r':TRIG:SLOP POS')
    # command_strings.append(r':OUTP:LOAD INF')
    # command_strings.append(r':BURS:STAT ON')
    # command_strings.append(r':BURS:MODE GAT')
    # command_strings.append(r':BURS:GATE:POL NORM')
    # command_strings.append(r':OUTP ON')
    # 
    # command_total = ''
    # for s in command_strings:
    #     command_total += (s + ';')
    # 
    # inst.write(command_total)

    # Uncomment the above if using GPIB instead of rs232
    command_strings = []
    command_strings.append(r':FUNC SIN')
    command_strings.append(r':VOLT %.4f V' % Vamp)  # Vpp
    command_strings.append(r':FREQ %.4f' % freq)  # Hz
    command_strings.append(r':VOLT:OFFS %.4f V' % Voff)
    command_strings.append(r':TRIG:SOUR EXT')
    command_strings.append(r':TRIG:DEL MIN')
    command_strings.append(r':TRIG:SLOP POS')
    command_strings.append(r':OUTP:LOAD INF')
    command_strings.append(r':BURS:STAT ON')
    command_strings.append(r':BURS:MODE GAT')
    command_strings.append(r':BURS:GATE:POL NORM')
    command_strings.append(r':OUTP ON')

    for command in command_strings:
        inst.write(command)
        time.sleep(.02)



    

rm = pyvisa.ResourceManager()
print(rm.list_resources())
inst = rm.open_resource('COM4', baud_rate=115200, parity=Parity.none)

print(inst.query("*IDN?"))

# If using RS232 instead of GPIB, there will be an error because too many commands are sent for the buffer
gated_sine(inst, 1, 0, 0.5e6)
print(inst.query("SYSTem:ERRor?"))

inst.close()

