"""Plot atom number as a function of a scanned global.

This multishot script still needs a lot of work. It doesn't handle averaging
results from identical repeated shots, it can't handle 2-parameter scans, and it
likely errors if no parameters are scanned.
"""
import matplotlib.pyplot as plt
import numpy as np

from lyse import Run, data, path
from analysislib.RbLab.lib.data_classes import Dataset, Shot
from analysislib.RbLab.lib.multishot_utils import get_dataframe_subset

# Get dataframe from Lyse.
df = data(n_sequences=1)
df_subset = df

# Get a subset of the Lyse dataframe containing only the shots to analyze.
# df_subset = get_dataframe_subset()

# Construct a Dataset instance
separate_sequences = df_subset['separate_sequences'][-1]
dataset = Dataset(df_subset, separate_sequences=separate_sequences)

# Find out what variables were scanned.
independents = dataset.get_independent_globals()

# Make the plot.
# axes = dataset.plot_lines(independents[0], 'atom_number')
# Need to determine how to appropriately do multishot averaging using the
# Dataset class. For now we'll just use the singleshot results from the
# dataframe.
x_variable = independents[0]
x_values = df[x_variable].values
y_values = df[('shot_results', 'atom_number')].values
fig = plt.figure(111)
axes = fig.add_subplot(111)
axes.plot(x_values, y_values, linestyle='-', marker='o')
axes.set_xlabel(x_variable)
axes.set_ylabel('Atom Number')
plt.tight_layout()
