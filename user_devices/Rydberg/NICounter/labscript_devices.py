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

from labscript import TriggerableDevice
from labscript.labscript import set_passed_properties
import numpy as np

class NICounter(TriggerableDevice):

    # A human readable name for device model used in error messages
    description = "NI Counter 6602"
    # The labscript Output classes this device supports
    allowed_children = [ ]
    # The maximum update rate of this device (in Hz)
    clock_limit = 1e6

    @set_passed_properties(
        property_names={
            'connection_table_properties':
                [
                    'name',
                    'MAX_name',
                    'counter_channel',
                    'input_channel',
                    'gate_channel',
                    'minimum_recovery_time'
                ]
        }
    )
    def __init__ ( self, name, parent_device, MAX_name, counter_channel, input_channel, gate_channel, connection='trigger', minimum_recovery_time=15e-8, **kwargs):
        """
            MAX_name: name of the device in the NI_MAX program
            counter_channel: The 6602 has several internal channels used for counting edges. There are 8 options, and choosing a different one shouldn't affect wiring or anything else
            input_channel: the channel to count the rising edges on
            gate_channel: this triggers the counter to start counting edges
            connection: informs labscript how the trigger is done. Any nonempty string works, and is overwritten
            minimum_recovery_time: minimum time between successive triggers
        """
        TriggerableDevice.__init__ ( self, name, parent_device, connection)
        self.BLACS_connection = "{}, Counter Channel:{}, Input Channel:{}".format(str(MAX_name), str(counter_channel), str(input_channel))
        self.name = name
        self.MAX_name = MAX_name
        self.counter_channel = counter_channel
        self.input_channel = input_channel
        self.gate_channel = gate_channel

        self.minimum_recovery_time = minimum_recovery_time
        self.acquire_time = None
        self.acquire_bins = []

    def generate_code(self,hdf5_file):
        """Write the command sequence to the HDF file

        Args:
            hdf5_file (hdf): labscript hdf file
        """

        TriggerableDevice.generate_code(self, hdf5_file)


        grp = hdf5_file.require_group(f'/devices/{self.name}/')
        
        if self. acquire_time is not None:
            dset_acquire_time = grp.require_dataset('acquire_time', (1,), dtype='f')
            dset_acquire_duration = grp.require_dataset('acquire_bins', (len(self.acquire_bins),), dtype='f')

            dset_acquire_time[0] = self.acquire_time
            dset_acquire_duration[0] = self.acquire_bins


    def acquire(self, time_start, duration):
        """acquire counts at a given time and for a given duration. The output is in the traces HDF folder and the first bin of the array should correspond to
        the number of counts in the acquire time

        Args:
            time_start ([float]): the time at which acquisition begins in seconds
            duration (float): the duration of the acquisition in seconds
        """     

        self.acquire_time = time_start
        self.acquire_bins = [duration]

        self.parent_device.trigger(self.acquire_time, self.minimum_recovery_time)
        self.parent_device.trigger(self.acquire_time+self.acquire_bins, self.minimum_recovery_time)

    def acquire_multiple(self, time_start, trigger_spacings):
        """acquire counts at a given time and for a given list of trigger spacings. The output is in the traces HDF folder. All elements after the first are the
        # of counts in each bin

        Args:
            time_start ([float]): the time at which acquisition begins in seconds
            trigger_spaces ([float list]): times (in seconds) to trigger the card. The output will be the binned number of counts between each trigger
        """     

        self.acquire_time = time_start
        self.acquire_bins = trigger_spacings

        minimum_PB_recovery_time = 20e-9 # the pulseblaster needs some time to recover before the next trigger. Give it 20ns
        trigger_time = self.acquire_time
        for trigger_duration in self.acquire_bins:
            self.parent_device.trigger(trigger_time, trigger_duration-minimum_PB_recovery_time)
            trigger_time += trigger_duration
        
        # trigger one more time to denote the end of the triggering sequence
        self.parent_device.trigger(trigger_time)



        
            


