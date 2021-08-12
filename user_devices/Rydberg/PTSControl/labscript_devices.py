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

from configparser import Error
from labscript import TriggerableDevice
from labscript.labscript import set_passed_properties
import numpy as np
from pathlib import Path


class PTSControl(TriggerableDevice):

    # A human readable name for device model used in error messages
    description = "Opal Kelly PTS Control"
    # The labscript Output classes this device supports
    allowed_children = [ ]
    # The maximum update rate of this device (in Hz). I am not sure about the FPGA update rate but thought this was a reasonable guess
    clock_limit = 1e3

    @set_passed_properties(
        property_names={
            'connection_table_properties':
                [
                    'name',
                    'device_serial',
                    'path_dictionary'
                ]
        }
    )
    def __init__ ( self, name, device_serial, parent_device, connection='trigger', **kwargs):
        """ initialize device

        Args:
            name (str): name of
            device_serial (int): The FPGA serial ID #: ['10440000KE','10440000K8'] = [probe, control]
        """
        TriggerableDevice.__init__ (self, name, parent_device, connection)
        self.BLACS_connection = "PTS Control FPGA ID:{}".format(device_serial)
        self.name = name
        # serial # of device
        self.device_serial = device_serial
        self.command_list = []
        # also not sure about the minimal time between triggers but seems reasonable based on the fact that this is ~4 clock cycles of the FPGA according to the thesis
        self.minimum_recovery_time = 1e-7
        self.path_dictionary = {
            "Fast Ramp Up":"fastcontrolUP.bit",
            "Fast Ramp Down":"fastcontrolDN.bit",
            "Slow Control":"slowcontrol.bit"
        }
        # which of the above modes the PTS is operating in
        self.mode = None
        # minimum, maximum, and step frequency. In slow mode, min = max freq. All in MHz
        self.max_freq = None
        self.min_freq = None
        self.step_freq = None



    def generate_code(self,hdf5_file):
        """Write the command sequence to the HDF file

        Args:
            hdf5_file (hdf): labscript hdf file
        """

        TriggerableDevice.generate_code(self, hdf5_file)

    
        grp = hdf5_file.require_group(f'/devices/{self.name}/')
        
        #S30 means string with 30 characters (in UTF-8)
        dset_min_max_step = grp.require_dataset('min_max_step_freq', (3,),dtype='f')
        dset_mode = grp.require_dataset('mode', (1,), dtype='S30')

        #encode and write command_list as an ascii string for each string in the list. This is necessary because HDF5 does not like regular strings or something
        dset_min_max_step[0] = self.min_freq
        dset_min_max_step[1] = self.max_freq
        dset_min_max_step[2] = self.step_freq
        dset_mode[0] = self.mode


    def program_single_freq(self, freq):
        if self.mode == None:
            raise RuntimeError("Set the PTS Mode before trying to program the frequency")

        self.min_freq = freq
        self.max_freq = freq

    def program_ramp_freq(self, min_freq, max_freq, step_freq):
        if self.mode == None:
            raise RuntimeError("Set the PTS Mode before trying to program the frequency")

        self.min_freq = min_freq
        self.max_freq = max_freq
        self.freq_step = step_freq


    def set_mode(self, mode_string):
        
        self.mode = self.path_dictionary[mode_string]


