import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from lyse import Run, data, path
from pathlib import Path
from matplotlib.widgets  import RectangleSelector
from analysislib.Rydberg.analysis_utils.labrad_fitting_utils import (
    read_spcm_continuous_monitor,
    write_spcm_continuous_monitor)
from analysislib.Rydberg.analysis_utils.labrad_fitting_routines import find_atom_number, gaussian
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning) 

COLOR = 'white'
mpl.rcParams['text.color'] = COLOR
mpl.rcParams['axes.labelcolor'] = COLOR
mpl.rcParams['xtick.color'] = COLOR
mpl.rcParams['ytick.color'] = COLOR


# Get the pandas series with all of the globals etc. for this shot
ser = data(path)

# Get the Run instance with all of the shot's acquired data, such as
# images, traces, and results from analysis.
run = Run(path)

spcm_counts_array = run.get_trace('spcm_counts')
spcm_value = spcm_counts_array[1]

# if a sequence is repeated, it is of the form ...rep00xxx.h5, so -8 through -3 give the indices of the rep #
# the first time the sequence is run though, it is of the form {sequence_name}_0.h5, so we call this run 0
try:
    run_number = int(path[-8:-3])
except:
    run_number = 0
prev_data = read_spcm_continuous_monitor(path)
data = prev_data.append({'run': run_number, 'counts':spcm_value}, ignore_index=True)
write_spcm_continuous_monitor(path, data)


fig = plt.figure(constrained_layout=True)

fig.patch.set_facecolor('xkcd:black')
gs = fig.add_gridspec(1, 1)
ax = fig.add_subplot(gs[0, 0])
ax.spines['left'].set_color(COLOR)       
ax.spines['bottom'].set_color(COLOR) 
ax.plot(data['run'], data['counts'], c='r')



