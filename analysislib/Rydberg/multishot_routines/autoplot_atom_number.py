"""Automatically plot atom number as a function of the varied parameters.

Note: This script was never quite completed because we decided to do our
analysis in jupter notebooks instead. It probably doesn't work at all and is
only retained for reference in case we decide to do more analysis inside of lyse
itself.

Partially based on y_vs_auto.py from Philip Starkey's thesis.

* If the same shot is repeated many times without changing any parameters, this
script plots atom number as a function of shot index.
* If one variable is changed, this script plots a line giving atom number as a
function of that parameter.
* TODO: If two parameters are scanned, this script makes a color plot where the
color corresponds to the atom number and the two axes are the two scanned
parameters.
* If three or more parameters are scanned, this script plots many lines where
the x-axis gives the value of one of the parameters, then each combination of
the other parameters is plotted as one line.
"""
import matplotlib.pyplot as plt
import numpy as np

from lyse import Run, data, path
from analysislib.RbLab.lib.multishot_utils import (
    get_dataframe_subset, get_independents
)


def plot_0D(df, y_parameter_tuple):
    # Get the values for the x-axis
    x_parameter = 'shot_repetition_index'
    x_data = df[x_parameter]
    x_values = x_data.values

    # Iterate over the quantities to plot, making one plot per quantity
    for y_parameter in y_parameter_tuple:
        # Extract the y values from the dataFrame
        # TODO: Use aliases for cleaner access to script results? e.g.:
        # y = df[get_alias(aliases, y_parameter, y_parameter)]
        # TODO: Ensure that shots are sorted by time or shot_index
        # TODO: Average over shot_repetion_index
        # TODO: Ensure that plot_0D still works after adding averaging code
        y_data = df[y_parameter]
        y_values = y_data.values

        # Create the figure and plot the results
        fig = plt.figure()
        plt.plot(x_values, y_values)

        # Add labels to the plot axes and a title
        plt.xlabel("shot_repetition_index")
        plt.ylabel(str(y_parameter))
        plt.title(plot_title)
        fig.tight_layout()

        # Print out the mean and standard deviation of the data
        mean = np.mean(y_values)
        std = np.std(y_values)
        percentage = std / mean * 100
        info_string = (f"{y_parameter}: mean = {mean:.3}, std = {std:.3}, "
                       f"std/mean = {percentage:.3}%")
        print(info_string)


def plot_1D(df, x_parameter, y_parameter_tuple):
    # Get the values for the x-axis
    x_data = df[x_parameter]
    x_values = x_data.values

    # Iterate over the quantities to plot, making one plot per quantity
    for y_parameter in y_parameter_tuple:
        # Extract the y values from the dataFrame
        # TODO: Use aliases for cleaner access to script results? e.g.:
        # y = df[get_alias(aliases, y_parameter, y_parameter)]
        # TODO: Ensure that shots are sorted by time or shot_index
        # TODO: Average over shot_repetion_index
        # TODO: Ensure that plot_0D still works after adding averaging code
        y_data = df[y_parameter]
        y_values = y_data.values

        # Create the figure and plot the results
        fig = plt.figure()
        plt.plot(x_values, y_values)

        # Add labels to the plot axes and a title
        plt.xlabel("shot_repitition_index")
        plt.ylabel(str(y_parameter))
        plt.title(plot_title)
        fig.tight_layout()


# Begin actual analysis script

# Get the relevant part of the Lyse dataframe
df = get_dataframe_subset()

# Get a list of the distinct values for 'sequence' in the lyse dataframe.
sequence_names_included = list(df['sequence'])
sequence_names_included = np.intersect1d(
    sequence_names_included,
    sequence_names_included,
)
sequence_names_included = [str(seq) for seq in sequence_names_included]

# Generate a plot title that contains the sequences we are plotting
plot_title = ', '.join([x for x in sequence_names_included])  # + '\n\n'

# Figure out if we should average repeated shots from different sequences (i.e.
# different clicks of 'Engage' in runmanager) or keep them separate. Use setting
# from last shot in dataframe.
separate_sequences = df['separate_sequences'][-1]

# Get the units for all of the globals
last_run = Run(df['filepath'][-1])
units = last_run.get_units()

# Figure out which globals were scanned
independents = get_independents(last_run)

# Plot things appropriately given the dimension of the scan.
# TODO: get y_parameter_tuple from globals. Maybe call it plot_parameters_tuple
# since it may be the y-axis or may be color-axis
# y_parameter_tuple = (
#     ('on_the_fly_absorption_image_processing', 'atom_number'),)
# n_independents = len(independents)
# if n_independents == 0:
#     plot_0D(df, y_parameter_tuple)
# elif n_independents == 1:
#     plot_1D(df, independents[0], y_parameter_tuple)

# Figure out what parameter to use for the x-axis
# TODO: Make it possible to select x_parameter, maybe using a global
if independents:
    x_parameter = independents[0]
else:
    x_parameter = 'shot_repetition_index'

# Set which parameters need to be the same for points to be part of the same
# line in the plot.
# Set whether different sequences are plotted separately or averaged
if separate_sequences:
    # In this case we should add 'sequence' to the list of things we use to
    # decide which points should be on distinct lines in the plot
    groupby_list = ['sequence'] + independents.copy()
else:
    groupby_list = independents.copy()
# Don't put points that only differ by their x_parameter value in
# different lines
if x_parameter in groupby_list:
    groupby_list.remove(x_parameter)

if not groupby_list:
    # groupby isn't happy if groupby_list is empty. When it's empty we actually
    # just want groupby to pass through everything in one group. To do this we
    # pass it a function that just always returns True. This is a perfectly fine
    # use of groupby, although admittedly it is a little misleading to call this
    # variable groupby_list when it is not a list, but a function.
    def groupby_list(x): return True  # pylint: disable=function-redefined

# Give the index level 'sequence' a new name to avoid confusion with the column
# called 'sequence' otherwise groupby() throws an error
df.index.set_names('seq', level=0, inplace=True)

# Iterate over all combinations of parameters besides x_parameter
atom_number_figure = plt.figure()
atom_number_axes = plt.subplot(111)
for line_parameters, df_subset in df.groupby(groupby_list):
    # line_parameters is a tuple of all the values for all the parameters
    # included in groupby_list
    # df_subset is a subset the of the Lyse dataframe which only includes the
    # rows that have the values line_parameters for the elements included in
    # groupby_list. Each subset is the data that should be included in each
    # line.

    # Iterate over the points in this line
    x_values = []
    atom_numbers = []
    atom_number_uncertainties = []
    for x_value, df_identical_shots in df_subset.groupby(x_parameter):
        # x_value is the value of x_parameter for these shots
        # df_identical_shots is a subset of the dataframe which only has shots
        # with identical values for the variables in groupby_list. These may be
        # from different sequences, i.e. different clicks of 'Engage' in
        # Runmanager, if separate_sequences is False.
        atom_number_data = df_identical_shots[(
            'shot_results', 'atom_number')]
        atom_number_average = atom_number_data.mean()
        atom_number_uncertainty = atom_number_data.std()
        # The uncertainty will be nan if there is only one shot

        # Collect results
        x_values.append(x_value)
        atom_numbers.append(atom_number_average)
        atom_number_uncertainties.append(atom_number_uncertainty)

    # Now plot the line for this line_parameters set
    # atom_number_axes.plot(x_values, atom_numbers, label=str(line_parameters))
    atom_number_axes.errorbar(
        x_values,
        atom_numbers,
        yerr=atom_number_uncertainties,
        fmt='-o',
        markersize=4,
        capsize=2,
        label=str(line_parameters),
    )

# Add legend
atom_number_axes.set_title(plot_title)
atom_number_axes.set_xlabel(f"{x_parameter} ({units[x_parameter]})")
atom_number_axes.set_ylabel('Atom Number')
atom_number_axes.legend()
atom_number_figure.tight_layout()


# Debug


def display_variable(variable_name):
    print(f"{variable_name} = {eval(variable_name)}")


# display_variable('independents')

# To save this result to the output hdf5 file, we have to instantiate a
# Sequence object:
# some_calculated_value =
# seq = Sequence(path, df)
# seq.save_result('some_calculated_value',some_calculated_value)

# TODO:
# * Get a similar script working for temperature
# * Move functions into a seperate module for reuse?
# * Write analysis code in Jupyter
#      * Use runmanager API to run the sequence and analyze the data all from
#        the notebook?
#      * Copy over hdf5 files to analysis computer(?)
#           * Could have Lyse script on control computer send shots to Lyse on
#             analysis computer, which then has a script to copy them over
