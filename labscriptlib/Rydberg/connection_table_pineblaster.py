from labscript_devices.NI_DAQmx.labscript_devices import NI_PCI_6713
from labscript import start, stop
import numpy as np
from labscript_devices.PineBlaster import PineBlaster
from labscript import (
    AnalogIn,
    AnalogOut,
    ClockLine,
    DDS,
    DigitalOut,
    MHz,
    Shutter,
    StaticDDS,
    WaitMonitor,
    start,
    stop,
    wait,
)

def cxn_table():

    PineBlaster(
        name="pineblaster_0",
        trigger_connection="port0/line15",
        usbport="COM4",
    )

    NI_PCI_6713(name = "ni_card_1", parent_device = pineblaster_0.clockline, clock_terminal = "/Dev2/PFI0", MAX_name = "Dev2")

    AnalogOut(
        name="analog1",
        parent_device=ni_card_1,
        connection="ao6"
    )


    AnalogOut(
        name="analog2",
        parent_device=ni_card_1,
        connection="ao5"
    )

if __name__ == '__main__':

    cxn_table()
    start()
    
    stop(1)