"""A library of parts of sequences that are common to many sequences.

This module is intended to be used to store functions that generate parts of
sequences. In particular, this module is intended to store common subsequences
that will be used in many sequences, such as those for loading the MOT or doing
absorption imaging. More unique/specific subsequences should be stored
elsewhere, possibly in the same file as the sequence that uses it. Additionally,
helper functions and the like that control outputs but that don't quite qualify
as making subsequences are stored in sequence_utils.py. For example, the
function open_shuttered_beam() which turns off a beam's AOM, opens its shutter,
then turns on the AOM at the desired time is stored in sequence_utils.py. On the
other hand, the function load_mot() has all of the code that sets all of the
outputs to load the MOT, so it is stored here. Note that some functions from
sequence_utils.py are imported directly into the namespace of this module with
the "from bar import foo" style syntax (e.g.open_shuttered_beam()), which means
that they are actually accessible by importing this module just as if they were
defined in this module.
"""
# parts lifted from Zak's code

import warnings

import numpy as np

import labscript as lab
import labscriptlib.Rydberg.Subseqeuences_Utils.Sequence_Utils as utils


def load_mot(start_time, duration, enable_mot=True, reset=False,
             marker_name="MOT"):
    """Here we load the MOT using parameters set in the globals file

    Args:
        start_time (float): the time at which the mot loading begins
        duration (float): length of the mot loading time in seconds
        enable_mot (bool, optional): whether or not to open the shutters (currently we have no shutters). Defaults to True.
        reset (bool, optional): We use this parameter to reset the MOT parameters as preparation for the start of the next sequence. When true, this functions acts to reset the MOT at the end of the sequence. Defaults to False.
        marker_name (str, optional): Name of the marker to put in runviewer. Defaults to "MOT".

    Returns:
        float: the length of the load_mot duration in seconds
    """
    # give the cards time to reset
    start_time += 1e-3
    lab.add_time_marker(start_time, marker_name)

    # set up coils
    utils.jump_from_previous_value(big_x_coil, start_time, MOT_BIG_X_COIL)
    #utils.jump_from_previous_value(big_z_coil, start_time, MOT_BIG_Z_COIL)
    #utils.jump_from_previous_value(small_x_coil, start_time, MOT_SMALL_X_COIL)
    utils.jump_from_previous_value(small_y_coil, start_time, MOT_SMALL_Y_COIL)
    utils.jump_from_previous_value(small_z_coil, start_time, MOT_SMALL_Z_COIL)
    utils.jump_from_previous_value(gradient_coil, start_time, MOT_GRADIENT_COIL)

    if MOT_GRADIENT_SWITCH:
        gradient_coil_switch.constant(start_time, 5)

    # set up laser AOMs
    utils.jump_from_previous_value(motl_aom_power, start_time, MOT_MOTL_POWER)
    utils.jump_from_previous_value(repump_aom_power, start_time, MOT_REPUMP_POWER)
    utils.jump_from_previous_value(dt852_aom_power, start_time, MOT_DT852_POWER)
    utils.jump_from_previous_value(dt1064_aom_power, start_time, MOT_DT1064_POWER)

    if MOT_MOTL_SWITCH:
        motl_aom_switch.enable(start_time)
    if MOT_REPUMP_SWITCH:
        repump_aom_switch.enable(start_time)
    if MOT_DT852_SWITCH:
        dt852_aom_switch.enable(start_time)
    if MOT_DT1064_SWITCH:
        dt1064_aom_switch.enable(start_time)

    #TODO: If enable=false turn off shutters (once we have shutters)

    return duration

def reset_mot(start_time, reset_mot_duration=1e-3, marker_name="Reset MOT"):
    """Set the outputs to their MOT values to prepare for the next shot.

    This subsequence should be run at the end of a shot. It sets the outputs of all of the channels to their MOT
    values so that everything is ready for the next shot.

    If the global `enable_mot_between_shots` is `True` then this will turn on
    the MOT and start loading atoms. If it is `False` then all of the outputs
    will go to their MOT values

    Args:
        start_time (float): (seconds) Time in the sequence at which to start
            resetting the MOT outputs. Note that the MOT coil will actually be
            instructed to start turning on sooner than this though; see the
            notes above.
        reset_mot_duration (float): (seconds) the time between resetting the MOT and ending the sequence
        marker_name (str): (Default="Reset MOT") The name of the marker to use
            in runviewer for this subsequence.

    Returns:
        duration (float): (seconds) Time needed to reset the outputs to their
            MOT values.
    """


    # Call load_mot() with the appropriate arguments, which takes care of the
    # other outputs.
    duration = load_mot(
        start_time,
        reset_mot_duration,
        enable_mot=True,
        reset=True,
        marker_name=marker_name,
    )

    # Trigger the MOT and REPUMP AD9599 so that it steps to the last frequency programmed, which is the same as the first frequency we program
    motl_trigger.trigger_next_freq(start_time)
    repump_trigger.trigger_next_freq(start_time)

    # Ensure that the last edge isn't cut off by the end of the sequence by
    # adding one more millisecond.
    duration = duration + 1e-3

    return duration

def compress_mot(start_time, duration, marker_name="CMOT"):
    """Here we load the MOT using parameters set in the globals file

    Args:
        start_time (float): the time at which the mot loading begins
        duration (float): length of the mot loading time in seconds
        enable_mot (bool, optional): whether or not to open the shutters (currently we have no shutters). Defaults to True.
        reset (bool, optional): We use this parameter to reset the MOT parameters as preparation for the start of the next sequence. When true, this functions acts to reset the MOT at the end of the sequence. Defaults to False.
        marker_name (str, optional): Name of the marker to put in runviewer. Defaults to "MOT".

    Returns:
        float: the length of the load_mot duration in seconds
    """
    lab.add_time_marker(start_time, marker_name)

    # # set up coils
    utils.ramp_from_previous_value(big_x_coil, start_time, 10e-3, 0.28, samplerate=1e5)
    utils.ramp_from_previous_value(small_z_coil, start_time, 9.5e-3, 0.1, samplerate=1e5)
    utils.ramp_from_previous_value(small_z_coil, start_time+0.01, 14.5e-3, 0.15, samplerate=1e5)
    utils.ramp_from_previous_value(small_z_coil, start_time+0.025, 14.5e-3, 0.27, samplerate=1e5)
    utils.ramp_from_previous_value(gradient_coil, start_time, 10e-3, 3.1, samplerate=1e5)

    # # set up laser AOMs
    utils.jump_from_previous_value(motl_aom_power, start_time+29e-3, 1.2)
    utils.ramp_from_previous_value(motl_aom_power, start_time+30e-3, 15e-3, 0.9, samplerate=1e5)
    motl_aom_switch.disable(start_time + 90e-3)
    utils.jump_from_previous_value(repump_aom_power, start_time+10e-3, 0.045)
    utils.jump_from_previous_value(dt852_aom_power, start_time, CMOT_DT852_POWER)
    utils.jump_from_previous_value(dt1064_aom_power, start_time, CMOT_DT1064_POWER)

    motl_trigger.trigger_next_freq(start_time)

    # uncomment if you want capability to turn these off after the MOT stage
    # if CMOT_MOTL_SWITCH:
    #     motl_aom_switch.enable(start_time)
    # if CMOT_REPUMP_SWITCH:
    #     repump_aom_switch.enable(start_time)
    # if CMOT_DT852_SWITCH:
    #     dt852_aom_switch.enable(start_time)
    # if CMOT_DT1064_SWITCH:
    #     dt1064_aom_switch.enable(start_time)


    return duration

def cmot_image(start_time, duration, marker_name='CMOT_image'):
    """Here is the code to take a CMOT image. Values are currently hardcoded,
    but when we get a better handle on labscript we should change them so that
    we read things in from a globals file and also optimize the ramping

    Args:
        start_time (float): the time the image begins
        duration (float): the time the imaging sequence ends. Added an extra 0.0005s to ensure values were reached in requisite amount of time
        marker_name (str, optional): The name of the image sequence in runviewer. Defaults to 'CMOT_image'.

    Returns:
        float: duration of the sequence in seconds
    """

    lab.add_time_marker(start_time, marker_name)

    utils.ramp_from_previous_value(big_x_coil, start_time+100e-6, 400e-6, 0.16, samplerate=1e5)
    # can make this bad code into a piecewise linear ramp from zak's utils functions 
    utils.ramp_from_previous_value(small_y_coil, start_time+100e-6, 400e-6, 1, samplerate=1e5)
    utils.ramp_from_previous_value(small_y_coil, start_time+0.032, 0.028, 0.3, samplerate=1e5)
    utils.jump_from_previous_value(small_z_coil, start_time+0.032, 0.05)

    utils.jump_from_previous_value(gradient_coil, start_time, 0)
    gradient_coil_switch.constant(start_time, 0)

    utils.ramp_from_previous_value(gradient_coil, start_time+0.01, 0.05, 1.68, samplerate=1e5)
    gradient_coil_switch.constant(start_time+0.01, 5)

    motl_trigger.trigger_next_freq(start_time)
    motl_trigger.trigger_next_freq(start_time+0.005)

    imaging_aom_power.constant(start_time, 0.15)
    basler.expose(start_time+0.0025,  'CMOT', 'atoms', 50e-6)
    imaging_aom_switch.enable(start_time+0.0025)
    imaging_aom_switch.disable(start_time+0.00255)

    imaging_aom_switch.enable(start_time+0.055)
    basler.expose(start_time+0.055, 'CMOT', 'no_atoms', 50e-6)
    imaging_aom_switch.disable(start_time+0.0555)
    imaging_aom_power.constant(start_time+0.0555, 0)

    repump_aom_power.constant(start_time, 0.1)

    repump_aom_switch.disable(start_time)
    repump_aom_switch.enable(start_time+500e-6)
    repump_aom_switch.disable(start_time+700e-6)

    return duration

def mot_image(start_time, duration, marker_name='MOT_image'):
    """Here is the code to take a MOT image. Values are currently hardcoded,
    but when we get a better handle on labscript we should change them so that
    we read things in from a globals file and also optimize the ramping

    Args:
        start_time (float): the time the image begins
        duration (float): the time the imaging sequence ends. Added an extra 0.0005s to ensure values were reached in requisite amount of time
        marker_name (str, optional): The name of the image sequence in runviewer. Defaults to 'MOT_image'.

    Returns:
        float: duration of the sequence in seconds
    """

    lab.add_time_marker(start_time, marker_name)

    utils.ramp_from_previous_value(small_y_coil, start_time+100e-6, 400e-6, 1, samplerate=1e5)
    utils.ramp_from_previous_value(small_y_coil, start_time+0.032, 0.028, 0.25, samplerate=1e5)

    utils.jump_from_previous_value(gradient_coil, start_time, 0)
    gradient_coil_switch.constant(start_time, 0)

    utils.ramp_from_previous_value(gradient_coil, start_time+0.01, 0.05, 1.68, samplerate=1e5)
    gradient_coil_switch.constant(start_time+0.01, 5)

    motl_trigger.trigger_next_freq(start_time)
    motl_trigger.trigger_next_freq(start_time+0.005)

    imaging_aom_power.constant(start_time, 0.15)
    basler.expose(start_time+0.001, name="MOT", frametype='atoms', trigger_duration=50e-6)
    imaging_aom_switch.enable(start_time+0.001)
    imaging_aom_switch.disable(start_time+0.00105)

    imaging_aom_switch.enable(start_time+0.055)
    basler.expose(start_time+0.055, name="MOT", frametype='no_atoms', trigger_duration=50e-6)
    imaging_aom_switch.disable(start_time+0.0555)
    imaging_aom_power.constant(start_time+0.0555, 0)

    repump_aom_switch.disable(start_time)
    repump_aom_switch.enable(start_time+500e-6)
    repump_aom_switch.disable(start_time+700e-6)

    return duration
