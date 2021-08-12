#####################################################################
#                                                                   #
# /example.py                                                       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the program labscript, in the labscript      #
# suite (see http://labscriptsuite.org), and is licensed under the  #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

# This script is to test the analog output and Arduino dds controller

import numpy as np
from labscript import (
    start,
    stop,
)

import time
import labscript as lab
# from labscript_utils import import_or_reload
#
# # Connection_Table
#
# import_or_reload(r"C:\Users\12566\PycharmProjects\SineWaveTest\SineWaveCxnTable.py")

from labscriptlib.Rydberg.connection_table import cxn_table
if __name__ == '__main__':
    cxn_table()
    rate = 1e6

    start()
    # For some reason this is required to make the PB trigger
    #pb_digital_out.go_high(0)

    t=0
    least.go_high(0)
    most.go_high(0)

    AWG1.program_gated_sine(5e6, #MHz
                            1, #V
                            0)

    stop(t+1)