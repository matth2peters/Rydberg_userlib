import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
from lyse import path, routine_storage
from pathlib import Path
from analysislib.Rydberg.analysis_utils.data_classes import Shot

COLOR = 'white'
mpl.rcParams['text.color'] = COLOR
mpl.rcParams['axes.labelcolor'] = COLOR
mpl.rcParams['xtick.color'] = COLOR
mpl.rcParams['ytick.color'] = COLOR

# Get the Run instance with all of the shot's acquired data, such as
# images, traces, and results from analysis.
run = Shot(path)

if not hasattr(routine_storage, 'previous_spcm_counts') or not hasattr(routine_storage, 'num_runs'):
            routine_storage.previous_spcm_counts = []
            routine_storage.num_runs = 0

current_spcm_counts_array = run.get_trace('spcm_counts')
spcm_value = current_spcm_counts_array[1]

routine_storage.previous_spcm_counts.append(spcm_value)
routine_storage.num_runs += 1

fig = plt.figure(constrained_layout=True)

fig.patch.set_facecolor('xkcd:black')
gs = fig.add_gridspec(1, 1)
ax = fig.add_subplot(gs[0, 0])
ax.spines['left'].set_color(COLOR)       
ax.spines['bottom'].set_color(COLOR) 
ax.plot(np.arange(0, routine_storage.num_runs), routine_storage.previous_spcm_counts, c='r')