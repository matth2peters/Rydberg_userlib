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

from collections import defaultdict
import time
from PyDAQmx import *
from PyDAQmx.DAQmxConstants import *
from PyDAQmx.DAQmxTypes import *
from PyDAQmx.DAQmxCallBack import *

import labscript_utils.h5_lock  # Must be imported before importing h5py.
import h5py
from matplotlib.pyplot import pause
import numpy as np
from labscript.labscript import set_passed_properties
import time


from blacs.tab_base_classes import Worker


class NICounterWorker(Worker):

    def init (self):
        # Once off device initialisation code called when the
        # worker process is first started .
        # Usually this is used to create the connection to the
        # device and/or instantiate the API from the device
        # manufacturer

        self.check_version()
        # Reset Device: clears previously added routes etc. Note: is insufficient for
        # some devices, which require power cycling to truly reset.
        DAQmxResetDevice(self.MAX_name)

        # when in a buffered mode (i.e. a sequence is executing) this is true
        self.buffered_mode = False
        # the maximum number of triggers you have in your sequence. Determines the size of the array containing the counts from your sequence
        # I set it to 500 because that seems like a high number, but this can be larger at the expense of making your HDF5 data file larger
        self.sample_buffer_len = 500

        self.task = None
        
    def check_version(self):
        """Check the version of PyDAQmx is high enough to avoid a known bug"""
        major = uInt32()
        minor = uInt32()
        patch = uInt32()
        DAQmxGetSysNIDAQMajorVersion(major)
        DAQmxGetSysNIDAQMinorVersion(minor)
        DAQmxGetSysNIDAQUpdateVersion(patch)

        if major.value == 14 and minor.value < 2:
            msg = """There is a known bug with buffered shots using NI DAQmx v14.0.0.
                This bug does not exist on v14.2.0. You are currently using v%d.%d.%d.
                Please ensure you upgrade to v14.2.0 or higher."""
            raise Exception(dedent(msg) % (major.value, minor.value, patch.value))


    def cleanup_task(self):
        """ clean up old task, ready to restart """

        if self.task is not None:
            self.task.StopTask()
            self.task.ClearTask()
            # I don't think the below line is necessary, but leaving it as a comment in case I find something doesn't work as expected later
            #DAQmxResetDevice(self.MAX_name)
            self.task = None

    def shutdown ( self ):
        # Once off device shutdown code called when the
        # BLACS exits
        self.cleanup_task()


    def program_manual ( self , front_panel_values ):
        # Update the output state of each channel using the values
        # in front_panel_values ( which takes the form of a
        # dictionary keyed by the channel names specified in the
        # BLACS GUI configuration
        # return a dictionary of coerced / quantised values for each
        # channel , keyed by the channel name (or an empty dictionary )
        return {}
        
    def transition_to_buffered ( self , device_name , h5_file_path,
    initial_values , fresh ):
        # Access the HDF5 file specified and program the table of
        # hardware instructions for this device .
        # Place the device in a state ready to receive a hardware
        # trigger (or software trigger for the master pseudoclock )
        #
        # The current front panel state is also passed in as
        # initial_values so that the device can ensure output
        # continuity up to the trigger .
        #
        # The fresh keyword indicates whether the entire table of
        # instructions should be reprogrammed (if the device supports
        # smart programming )
        # Return a dictionary , keyed by the channel names , of the
        # final output state of the shot file . This ensures BLACS can
        # maintain output continuity when we return to manual mode
        # after the shot completes .

        # the shot file path
        self.h5_filepath = h5_file_path
        self.buffered_mode = True
        self.ready_acquisition()
        
        final_values = {}
        return final_values

    def ready_acquisition(self):
        """Here we prepared the NI card for acquisition. It won't actually start counting until the gate trigger goes high

        """

        # clean up anything from previous tasks
        self.cleanup_task()
        # start a new task
        self.task = Task()
        # settings for counting the edges on the input channel
        self.task.CreateCICountEdgesChan(
            self.counter_channel,   # const char counter[]
            "",                     # const char nameToAssignToChannel[]
            DAQmx_Val_Rising,       # edge
            0,                      # initialCount
            DAQmx_Val_CountUp       # countDirection
        )

        # set up the gate channel
        self.task.CfgSampClkTiming(
                    self.gate_channel,      # source[]
                    1e6,                    # using 1 MHz to be a large value
                    DAQmx_Val_Rising,       # edge
                    DAQmx_Val_ContSamps,    # mode
                    self.sample_buffer_len  # sampsPerCHan
        )

        # set up the ability to transfer the data through Direct memory Access
        self.task.SetCIDataXferMech(
                    self.counter_channel,   #channel
                    DAQmx_Val_DMA,          #Mode
        )
        # start the task
        self.task.StartTask()


    def read_data(self):
        """Reads the data from the NI card

        Returns:
            [int array, int]: buffer contains an array where each element is the number of rising edges on the counter channel during the trigger. The number
            of elements is each to the number of times the card was triggered. Keep in mind the data will be stored on the card until there is a trigger *after*
            the first trigger. read is an integer that tells you how many times the card was triggered in the sequence
        """
        if self.task is None:
            return None
        
        # create a buffer to put our counts in
        buffer = np.zeros(self.sample_buffer_len, dtype=uInt32)
        # create an integer to read how many times we triggered
        read = int32()
        # read the actual data from the NI card
        self.task.ReadCounterU32(
            -1,                     # numSampsPerChan, read all samples in buffer 
            1.0,                    # timeout
            buffer,                 # readArray[]
            self.sample_buffer_len, # arraySizeInSamps
            byref(read),            # sampsRead
            None
        )
        # clean up the card start after reading
        self.cleanup_task()

        return buffer, read.value

    def transition_to_manual ( self ):
        # Called when the shot has finished , the device should
        # be placed back into manual mode
        # return True on success

        # here we save the data from the shot after it ends
        if self.buffered_mode:
            
            buffer, times_triggered = self.read_value()

            with h5py.File(self.h5_file, 'a') as hdf5_file:
                data_group = hdf5_file['data']
                data_group.require_group('traces')
                counts = data_group.require_dataset('spcm_counts', (len(buffer),), dtype='int32')
                        
                counts[:] = buffer

            self.h5_filepath = None
            self.buffered_mode = False

        return True

    def abort_transition_to_buffered ( self ):
        # Called only if transition_to_buffered succeeded and the
        # shot if aborted prior to the initial trigger
        # return True on success
        return True
    def abort_buffered ( self ):
        # Called if the shot is to be abort in the middle of
        # the execution of the shot ( after the initial trigger )
        # return True on success
        return True

