from labscript_devices.NI_DAQmx.labscript_devices import NI_PCI_6713
from labscript import start, stop, ClockLine, DigitalOut
import numpy as np
#from labscript_devices.DummyPseudoclock import DummyPseudoclock
from labscript_devices.PulseBlasterESRPro500_Edited import PulseBlasterESRPro500
#from labscript_devices.PulseBlasterESRPro500 import PulseBlasterESRPro500
from labscript_devices.PulseBlasterUSB import PulseBlasterUSB
from labscript_devices.IMAQdxCamera.labscript_devices import IMAQdxCamera
from user_devices.Rydberg.AD9959ArduinoComm.labscript_devices import AD9959ArduinoComm, AD9959ArduinoTriggerAnalog, AD9959ArduinoTriggerDigital
from user_devices.Rydberg.Agilent33250a.labscript_devices import Agilent33250a
from user_devices.Rydberg.PTSControl.labscript_devices import PTSControl
from user_devices.Rydberg.NICounter.labscript_devices import NICounter

from labscript import (
    AnalogOut,
    ClockLine,
    DigitalOut,
    MHz,
    Trigger,
    start,
    stop
)

def cxn_table():
    
    PulseBlasterESRPro500(
        name='pulseblaster_0',
        board_number=0
    )

    # PulseBlasterUSB(
    # name='pulseblaster_0',
    # board_number=0,
    # )

    # DummyPseudoclock(name='pseudoclock')

    # ClockLine(
    # name='clock0',
    # pseudoclock=pulseblaster_0.pseudoclock,
    # connection='flag 1',
    # )

    # DigitalOut(
    #     name='do_test',
    #     parent_device=pulseblaster_0.direct_outputs,
    #     connection='flag 0',
    #     default_value=1,
    # )   

    #see page 28 of the PB ESR Pro manual: these ensure that the pulses are actually output
    DigitalOut(
    name='pulse_len_least',
    parent_device=pulseblaster_0.direct_outputs,
    connection='flag 21',
    default_value=1,
    )   
    
    DigitalOut(
    name='pulse_len_middle',
    parent_device=pulseblaster_0.direct_outputs,
    connection='flag 22',
    default_value=1,
    )

    DigitalOut(
    name='pulse_len_most',
    parent_device=pulseblaster_0.direct_outputs,
    connection='flag 23',
    default_value=1,
    )

    # Trigger(
    #     name='counter_trigger',
    #     parent_device=pulseblaster_0.direct_outputs,
    #     connection='flag 7',
    #     default_value=0,
    # )

    # NICounter(
    #     name='counter', 
    #     parent_device=counter_trigger,
    #     MAX_name='Dev6', 
    #     counter_channel="Dev6/Ctr0", 
    #     input_channel="/Dev6/PFI39", 
    #     gate_channel="/Dev6/PFI38", 
    # )


    #NI_PCI_6713(name = "ni_card_1", parent_device = pineblaster_0.clockline, clock_terminal = "/Dev2/PFI0", MAX_name = "Dev2")
    #NI_PCI_6713(name = "ni_card_1", parent_device = ni_pci_6713_dev2_clock, clock_terminal = "/Dev2/PFI0", MAX_name = "Dev2")

    #Trigger(
    #    name='PTSControl_trigger',
    #    parent_device=pulseblaster_0.direct_outputs,
    #    connection='flag 0'
    #)

    #PTSControl(
    #    name='PTScontrol',
    #    parent_device=PTSControl_trigger,
    #    connection='trigger',
    #    device_serial=b'10440000K8',
    #)

    # AD9959ArduinoTriggerAnalog(
    # # *** SHOULD NOT EXCEED CLOCKING ARDUINO MORE
    # #    THAN ONCE PER 100 us!!! ***
    # name="MOT_step",
    # parent_device=ni_card_1,
    # connection="ao2",
    # default_value=0
    # )

    # AD9959ArduinoComm(
    #     name = "MOTRepump",
    #     parent_device=None,
    #     com_port = "COM3",
    #     baud_rate = 115200,
    #     channel_mappings={"ch0":"ch0", "ch1":"ch1"}
    # )

    AD9959ArduinoTriggerDigital(
        name="motl_trigger",
        parent_device=pulseblaster_0.direct_outputs,
        connection="flag 0",
        default_value=0,
    )

    AD9959ArduinoTriggerDigital(
        name="repump_trigger",
        parent_device=pulseblaster_0.direct_outputs,
        connection="flag 1",
        default_value=0,
    )

    AD9959ArduinoComm(
        name="motl_repump_ad9959",
        parent_device=None,
        com_port="COM12",
        baud_rate = 115200,
        channel_mappings={"MOT":'ch0', "Repump":'ch3'},
        div_32=True
    )

    # PB is too fast for arduino, use AO instead
    # arduino_step = DigitalOut(
    # name='arduino_step',
    # parent_device=pulseblaster_0.direct_outputs,
    # connection='flag 3',
    # default_value=0,
    # )   

    # AnalogOut(
    #     name="analog1",
    #     parent_device=ni_card_1,
    #     connection="ao6"
    # )



if __name__ == '__main__':

    cxn_table()
    start()
    stop(1)