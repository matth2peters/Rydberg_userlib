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

import time
from labscript import (
    start,
    stop,
)
import labscriptlib.Rydberg.Subseqeuences_Utils.Sequence_Utils as utils
from labscriptlib.Rydberg.Subseqeuences_Utils.Subsequences import cmot_image, load_mot, compress_mot, reset_mot, cmot_image
from labscriptlib.Rydberg.Rydberg_connection_table import cxn_table

if __name__ == '__main__':

    # Import and define the global variables for devices
    cxn_table()

    # Set the params that do not change over course of expt
    utils.set_static_parameters()
    t=0

    start()
    
    t+= load_mot(t, 1)

    t += compress_mot(t, 90e-3)

    t += cmot_image(t, duration=60e-3)

    t += reset_mot(t)

    stop(t)