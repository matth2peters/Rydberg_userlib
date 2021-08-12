#####################################################################
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

from labscript import IntermediateDevice, AnalogOut, TriggerableDevice
from labscript.labscript import AnalogQuantity, set_passed_properties
import numpy as np

class Agilent33250a(TriggerableDevice):

    # A human readable name for device model used in error messages
    description = "Agilent 33250A"
    # The labscript Output classes this device supports
    allowed_children = [ ]
    # The maximum update rate of this device (in Hz)
    clock_limit = 1e3

    @set_passed_properties(
        property_names={
            'connection_table_properties':
                [
                    'name',
                    'com_port',
                    'baud_rate',
                    'device_ID',
                    'RS_232'
                ]
        }
    )
    def __init__ ( self, name, parent_device, com_port, device_ID, connection='trigger', baud_rate = 115200, RS_232=False, **kwargs):
        """ initialize device

        Args:
            name (str): name of the device
            com_port (int): the comport the device is attached to 
            baud_rate (int, optional): The baud rate (rate of communication over serial). Defaults to 115200.
            device_ID (int): The GPIB port ID set on the device under Utility
            RS_232 (bool): should be true if using RS232 instead of GPIB -- RS232 has a slower communication rate and sometimes commands are lost
        """
        TriggerableDevice.__init__ (self, name, parent_device, connection)
        self.BLACS_connection = "Agilent 33250A {}, ID:{}".format(com_port , str(device_ID))
        self.name = name
        self.device_id = device_ID
        self.command_list = []
        self.com_port = com_port
        self.RS_232 = RS_232
        self.minimum_recovery_time = 1e-8
        self.baud_rate = baud_rate

    def generate_code(self,hdf5_file):
        """Write the command sequence to the HDF file

        Args:
            hdf5_file (hdf): labscript hdf file
        """ 

        TriggerableDevice.generate_code(self, hdf5_file)

        grp = hdf5_file.require_group(f'/devices/{self.name}/')
        
        # S30 means string with 30 characters (in UTF-8)
        dset = grp.require_dataset('command_list', (len(self.command_list),),dtype='S30')

        # encode and write command_list as an ascii string for each string in the list. This is necessary because HDF5 does not like regular strings or something
        dset[:] =  [n.encode("ascii", "ignore") for n in self.command_list]


    def program_gated_sine(self, freq, amplitude, offset):
        """set the frequency, amplitude, and offset in the list of command (as ), which will be used in the 
        generate code method

        Search "Publication Number 33250-90002 (order as 33250-90100 manual set) Edition 2, March 2003"
        or see https://docs.rs-online.com/4805/0900766b80ceb844.pdf for details on the other commands 
        and for error messages that may occur

        Args:

            freq: Frequency of the sine wave
            amplitude: amplitude of the sinewave in V
            offset: voltage offset for the sinewave 
        """
        # TODO: Make this all a single string when using GPIB
        
        self.command_list.append(r':OUTP OFF')
        self.command_list.append(r':FUNC SIN')
        self.command_list.append(r':VOLT %.4f V' % amplitude)  # Vpp
        self.command_list.append(r':FREQ %.4f' % freq)  # Hz
        self.command_list.append(r':VOLT:OFFS %.4f V' % offset) # Volts
        self.command_list.append(r':TRIG:SOUR EXT')
        self.command_list.append(r':TRIG:DEL MIN')
        self.command_list.append(r':TRIG:SLOP POS')
        self.command_list.append(r':OUTP:LOAD INF')
        self.command_list.append(r':BURS:STAT ON')
        self.command_list.append(r':BURS:MODE GAT')
        self.command_list.append(r':BURS:GATE:POL NORM')
        self.command_list.append(r':OUTP ON')

        if not self.RS_232:
            self.commandlist = ["".join(self.command_list)]

    def trigger(self, t, duration=1e-7):
        """Request parent trigger device to produce a trigger at time t with given
        duration."""
        # Only ask for a trigger if one has not already been requested by another device
        # attached to the same trigger:
        already_requested = False
        for other_device in self.trigger_device.child_devices:
            if other_device is not self:
                for other_t, other_duration in other_device.__triggers:
                    if t == other_t and duration == other_duration:
                        already_requested = True
        if not already_requested:
            self.trigger_device.trigger(t, duration)

        # Check for triggers too close together (check for overlapping triggers already
        # performed in Trigger.trigger()):
        start = t
        end = t + duration
        for other_t, other_duration in self.__triggers:
            other_start = other_t
            other_end = other_t + other_duration
            if (
                abs(other_start - end) < self.minimum_recovery_time
                or abs(other_end - start) < self.minimum_recovery_time
            ):
                msg = """%s %s has two triggers closer together than the minimum
                    recovery time: one at t = %fs for %fs, and another at t = %fs for
                    %fs. The minimum recovery time is %fs."""
                msg = msg % (
                    self.description,
                    self.name,
                    t,
                    duration,
                    start,
                    duration,
                    self.minimum_recovery_time,
                )
                raise ValueError(dedent(msg))

        self.__triggers.append([t, duration])
        




        
            


