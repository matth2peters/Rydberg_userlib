"""Perform a computationally intensive absorption image analysis.

This script does the same type of analysis as
on_the_fly_absorption_image_processing.py, but analyzes multiple images each
time it is called, and it uses far more beam images to perform the principal
component analysis. This makes the routine much slower and means that it must be
run on a computer with a lot of RAM. Therefore, this routine should NOT be run
on the control computer.

The script's name begins with "post" to imply that it should be used for post-
analysis of accumulated data rather than for processing data on-the-fly as it
comes in. This is due to the lengthy processing time required for this analysis.
"""
import numpy as np

from lyse import Run, data, path
from analysislib.RbLab.lib.absorption_image_processor import \
    AbsorptionImageProcessor
from analysislib.RbLab.lib.data_classes import Dataset, Shot
from analysislib.RbLab.lib.multishot_utils import get_dataframe_subset

# Get dataframe from Lyse
df = data()

# Get a subset of the Lyse containing only the shots to analyze
df_subset = get_dataframe_subset()

# Construct a Dataset instance
separate_sequences = df_subset['separate_sequences'][-1]
dataset = Dataset(df_subset, separate_sequences=separate_sequences)

# Configure settings
max_principal_components = df_subset['post_max_principal_components'][-1]

# TODO: Copy over new files from control computer to analysis computer?

# Construct an AbsorptionImageProcessor and add all beam images that had the
# desired ROI settings for the camera. That means same image size/shape as well
# as same region on the CCD.
# TODO: Keep that instance alive between calls to this script? Look into Lyse
# storage mentioned in Lyse MLOOP bitbucket page. Would need to think about what
# to put for max_beam_images and how/whether to downsample and use fewer beam
# images than we have available.
# Use beam images from all compatible shots in Lyse dataframe for now.
# Get roi values for last shot in dataframe
desired_roi = df_subset['camera', 'ROI'].iloc[-1].values
# Get roi values for all shots in dataframe. Gives a 2D numpy array, one row for
# each shot.
rois = df['camera', 'ROI'].values
# Iterate over rows and find which are equal to desired_roi.
selection = [np.array_equal(actual_roi, desired_roi) for actual_roi in rois]
# Get a dataframe subset with only shots that have the same ROI values.
df_beam_images = df[selection]
# Create an AbsorptionImageProcessor instance with the beam_images from all of
# these shots.
max_beam_images = len(df_beam_images.index)
processor = AbsorptionImageProcessor(max_beam_images=max_beam_images,
                                     max_principal_components=max_principal_components,
                                     use_sparse_routines=True)
for shot_path in df_beam_images['filepath']:
    shot = Shot(shot_path)
    processor.add_beam_image(shot)

# Mask atom region
atom_region_rows = df_subset['atom_region_rows'].iloc[-1]
atom_region_cols = df_subset['atom_region_cols'].iloc[-1]
processor.set_rectangular_mask(atom_region_rows, atom_region_cols)

# Perform the data analysis
dataset.process_images(processor)
dataset.fit_gaussians()
