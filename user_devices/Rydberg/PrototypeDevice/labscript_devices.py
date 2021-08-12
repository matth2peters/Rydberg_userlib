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

from labscript import IntermediateDevice
from labscript.labscript import set_passed_properties
import numpy as np

# Intermediate device is the class this one inherits from
# another option is TriggerableDevice, which you may want to use for a signal generator
# Example signal generator usage: programing an arb. waveform, then output the waveform when it receives a trigger
class PrototypeDevice(IntermediateDevice):

    # A human readable name for device model used in error messages
    description = "PrototypeDevice"
    # The labscript Output classes this device supports
    allowed_children = [ ]
    # The maximum update rate of this device (in Hz)
    clock_limit = 1e8 

    @set_passed_properties(
        property_names={
            'connection_table_properties':
                [
                    'name',
                    # add other properties here to put in the connection table! examples may be com ports, baud rates, etc.
                    # These are properties that can be accessed in the blacs_tabs class and passed on to the worker
                ]
        }
    )
    def __init__ (self, name, parent_device, **kwargs):
        """ initialize device

        Args:
            name (str): name of device
            com_port (int): the comport the device is attached to 
            baud_rate (int, optional): The baud rate (rate of communication over serial). Defaults to 115200.
            channel_mappings  (str, optional): the names of the channel. Example: {"MOT":"ch1", "Repump":"ch2"}.
            div_32 (bool): For the MOT and Repump frequencies, we divide them by 32 because of the frequency rescaling done by the AD4007
        """
        IntermediateDevice.__init__ ( self, name, parent_device, **kwargs)
        self.BLACS_connection = "PrototypeDevice: {}".format(name)
        self.name = name
        self.parent_device = parent_device
        self.command_list = []

    def generate_code(self,hdf5_file):
        """Write the frequency sequence for each channel to the HDF file

        Args:
            hdf5_file (hdf): labscript hdf file
        """

        IntermediateDevice.generate_code(self, hdf5_file)
        
        # Here we write custom instructions to the HDF file, which will be read in the workers class
        # In this example, I pass an encoded array of strings, which could be visa commands 
        # Other options are floats, integers, bytes, etc.
        grp = hdf5_file.require_group(f'/devices/{self.name}/')
        # S30 means string with 30 characters (in UTF-8)
        dset = grp.require_dataset('command_list', (len(self.command_list),),dtype='S30')
        # encode and write command_list as an ascii string for each string in the list. This is necessary because HDF5 does not like regular python strings
        dset[:] =  [n.encode("ascii", "ignore") for n in self.command_list]

    def labscript_sequence_method(self, programming_instructions):
        # Here you should define a method that allows you to program your device in a sequence. This should 
        self.command_list = programming_instructions