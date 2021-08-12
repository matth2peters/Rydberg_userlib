import numpy as np

from lyse import Run, path
from analysislib.Rydberg.analysis_utils.data_classes import Shot

# Get the Run instance with all of the shot's acquired data, such as
# images, traces, and results from analysis.
# run = Run(path)

# Create an instance of our custom Shot class. This class inherits from lyse.Run
# so it has all of that class's methods and more, and so it can be used in place
# of the lyse.Run class.
shot = Shot(path)

# Perform the fits
shot.fit_gaussians()
