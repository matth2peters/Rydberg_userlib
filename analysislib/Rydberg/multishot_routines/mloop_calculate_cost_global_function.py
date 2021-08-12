"""Calculate M-LOOP cost and uncertainty based on functions from globals.

Note: The way this script works is a bit janky. A better way to do things is to
use mloop_calculate_cost.py. As of this writing, this script does work though.

This script calculates and saves the cost and uncertainty for an M-LOOP
optimization based on functions defined in globals. Labscript doesn't support
saving functions as the values of globals directly, so we have to use a
workaround. Instead, put the python code to define your function inside a string
and this script will use that string to generate a python function using eval().
The code in the string can use python's lambda function feature to return a
function. If desired, values of other globals can be inserted into the function
by insterting them into the string using f-strings or other python string
formatting utilities.

Usage Instructions:
* Define a global called mloop_cost_function.
  * This global should be a string (NOT a function) giving code that returns a
    function when evaluated. The function should take a RepeatedShot instance
    and return the cost to be passed to M-LOOP. Example:
    'lambda repeatedshot: repeatedshot.atom_number'
* Define a global called mloop_cost_uncertainty_function.
  * This should be a string containing code for a function that takes a
    RepeatedShot instance and returns the uncertainty in the cost. Example:
    'lambda repeatshot: repeatedshot.atom_number_uncertainty'
  * This is essentially the same thing as mloop_cost_function, except that it
    should return the uncertainty in the cost instead of the cost itself.
* Set the mloop_config.ini file's cost_key to ["mloop_costs", "mloop_cost"].
* Ensure that this script is added to Lyse's multishot routines and is checked.
* Ensure that the singleshot routine on_the_fly_absorption_image_processing.py
  is checked.
* Start optimization by clicking "Run multishot analysis".
  * Starting the optimization by clicking engage in runmanager is probably a bad
    idea when using multiple shots per M-LOOP iteration.

Note that multishot routines in general run after the singleshot routines, which
means that a copy of the shot file will have been transferred over to the
analysis computer by transfer_files.py before this script is run, which means
that there are two copies of the file. We typically save any additional results
just to the copy on the analysis computer since that's the copy we use, but the
M-LOOP integration code will look for results in the original copy. Results
calculated here are saved to both copies using save_result_to_both_copies() from
multishot_utils.py. That way the M-LOOP integration code still works, but we
still get a complete copy of the shot file on the analysis computer.
"""
import os

import matplotlib.pyplot as plt
import numpy as np

from lyse import Run, data, path
from analysislib.RbLab.lib.data_classes import Dataset, Shot
from analysislib.RbLab.lib.multishot_utils import (
    check_all_shots_run, check_all_singleshot_run, get_dataframe_subset,
    save_result_to_both_copies,
)

# Get a subset of the Lyse dataframe containing only the shots to analyze.
df_subset = get_dataframe_subset(n_sequences_to_include=1)

# Check if the all of the shots from this call to engage in runmanager have
# completed.
all_shots_run = check_all_shots_run(df_subset)

# Check if the single shot routines have been run on all the shots from this
# call to engage in runmanager. Since the results here depend on results from
# on_the_fly_absorption_image_processing.py we have to make sure that the single
# shot routines run on all of the shots before we give results to M-LOOP.
# Sometimes a shot can be added after lyse starts running the multishot
# routines. That can lead to a scenario where all the shots have run but the
# single shot routines haven't been run on one or more of them.
all_singleshot_run = check_all_singleshot_run(df_subset)

# Create an instance of our custom Shot class. This class inherits from lyse.Run
# so it has all of that class's methods and more, and so it can be used in place
# of the lyse.Run class. We'll use the original copy since the M-LOOP script
# will look for results in that file.
shot_path = df_subset['filepath'].iloc[-1]
last_shot = Shot(shot_path)

# Set where results are saved for that shot file
results_group = 'results/mloop_costs'

if all_shots_run and all_singleshot_run:
    # All of the shots have completed, so do the analysis and save the result
    # for mloop_multishot.py
    print("All shots of engage have completed, generating results for mloop...")

    # Construct a Dataset instance
    dataset = Dataset(df_subset)

    # Do the standard analysis to get atom number, etc.. We won't redo the
    # absorption image processing, but we'll average and integrate the previous
    # results for individual shots.
    dataset.average_od_images()
    dataset.integrate_od_images()
    dataset.fit_gaussians()

    # Assume that there is only one repeatedshot instance in the dataset for
    # now. Later we may generalize to allow more than one repeatedshot to
    # analyze time-of-flight scan data, etc..
    repeatedshot = dataset.repeatedshot_list[0]

    # Calculate the cost.
    cost_function = eval(repeatedshot.mloop_cost_function)
    cost = cost_function(repeatedshot)
    save_result_to_both_copies(
        last_shot,
        'mloop_cost',
        cost,
        group=results_group,
    )

    # Calculate the cost uncertainty.
    uncertainty_function = eval(repeatedshot.mloop_cost_uncertainty_function)
    uncertainty = uncertainty_function(repeatedshot)
    # Save uncertainty with naming convention required by the mloop lyse
    # integration code.
    save_result_to_both_copies(
        last_shot,
        'u_mloop_cost',
        uncertainty,
        group=results_group,
    )

    # Print results.
    print(f"Cost: {cost} +/- {uncertainty}")
else:
    # In this case we're not ready for M-LOOP yet. We'll avoid running the
    # M-LOOP analysis by settings the results to nan.
    if not all_shots_run:
        print("Not all shots have run, skipping M-LOOP.")
    elif not all_singleshot_run:
        print("Single shot routines haven't run on all shots, skipping M-LOOP.")
    # Don't need to save results in this case. The M-LOOP integration code will
    # just get nan for mloop_cost and u_mloop_cost anyway since their entries
    # are empty in the dataframe.
