"""Perform absorbtion imaging analysis on the most recent identical shots.

This script is not quite finished; there is a TODO list below.

This script was written to perform absortion imaging analysis on multiple shots
in one go and average their results. It was written with the intent of using it
with M-LOOP. The idea was that doing this analysis in one go rather than doing
it for each shot individually might be faster. The difference between this
script and post_absorption_image_processing is that this script keeps an
absorption_image_processor instance alive and only uses the most recent shots
instead of all of the shots (with the appropriate ROI) in the lyse dataframe.

This multishot routine may be helpful outside of M-LOOP, as it allows you to
average results from multiple shots without having to go through the hassle of
setting up a jupyter notebook analysis section. It does assume that all of the
shots from the last call to engage() in runmanager have the same parameters and
should be average (otherwise it erros out) so it is not useful when doing scans.

TODO:
* Finish docstring
* Add images to absorption image processor from other shots in dataframe during
  its creation.
  * That way it can have a library of images ready for the first shot that it is
    supposed to analyze.
* Figure out how to deal with the way we copy shot files to the analysis
computer.
  * Save results to both copies of the file?
  * Copy file? with overwriting?
    * Maybe error if transfer_file.py single shot routine is checked?
"""
import time

import numpy as np

from lyse import data, routine_storage, Run
from analysislib.RbLab.lib.absorption_image_processor import AbsorptionImageProcessor
from analysislib.RbLab.lib.data_classes import Dataset
from analysislib.RbLab.lib.multishot_utils import (
    check_all_shots_run, check_all_singleshot_run, get_dataframe_subset,
)

# Keep track of how long this script takes to run.
start_time = time.time()

# Get a subset of the Lyse dataframe containing only the shots to analyze.
df_subset = get_dataframe_subset(n_sequences_to_include=1)

# Check if the all of the shots from this call to engage in runmanager have
# completed.
all_shots_run = check_all_shots_run(df_subset)

# Check if the single shot routines have been run on all the shots from this
# call to engage in runmanager.
all_singleshot_run = check_all_singleshot_run(df_subset)

if all_shots_run and all_singleshot_run:
    # Construct a Dataset intance to hold the shots.
    dataset = Dataset(df_subset)

    # This script is designed to average results from identical shots, so there
    # should only be one RepeatedShot instance in dataset.
    if len(dataset.repeatedshot_list) != 1:
        message = ('This script is designed to average results from identical '
                   'shots only, but not all of the shots in the most recent '
                   'call to engage() in runmanager have the same values for '
                   'globals.')
        raise RuntimeError(message)

    # Set options for when an AbsorptionImageProcessor instance is created.
    max_beam_images = int(
        df_subset['lyse_ms_on_the_fly_max_beam_images'].iloc[-1]
    )
    max_principal_components = int(
        df_subset['lyse_ms_on_the_fly_max_principal_components'].iloc[-1]
    )
    use_sparse_routines = True

    # Make function for creating a new AbsorptionImageProcessor since there are
    # a few spots below where we may need to do that.
    def create_new_absorption_image_processor():
        processor = AbsorptionImageProcessor(
            max_beam_images=max_beam_images,
            max_principal_components=max_principal_components,
            use_sparse_routines=use_sparse_routines,
        )
        routine_storage.on_the_fly_absorption_image_processor = processor
        return processor

    # Getting the processor from Lyse's routine_storage keeps it alive between
    # runs of this script, which makes it possible to keep background images
    # from previous shots.
    # Create a new absorption image processor if we don't have one going
    # already.
    if not hasattr(routine_storage, 'on_the_fly_absorption_image_processor'):
        processor = create_new_absorption_image_processor()

    # Get the absorption image processor.
    processor = routine_storage.on_the_fly_absorption_image_processor

    # Create a new processor if we want a different value for max_beam_images.
    if processor.max_beam_images != max_beam_images:
        processor = create_new_absorption_image_processor()

    # Ensure processor has desired value for max_principal_components.
    processor.max_principal_components = max_principal_components

    # Add the beam images to the processor.
    for shot in dataset.shot_list:
        try:
            processor.add_beam_image(shot)
        except ValueError:
            # Image shape has changed, can't use old beam_images anymore. We'll
            # create a new on_the_fly_absorption_image_processor.
            processor = create_new_absorption_image_processor()
            processor.add_beam_image(shot)

    # Make mask for atom region.
    atom_region_rows = dataset.last_shot.atom_region_rows
    atom_region_cols = dataset.last_shot.atom_region_cols
    processor.set_rectangular_mask(atom_region_rows, atom_region_cols)

    # Do the analysis on the images.
    dataset.process_images(processor)
    # dataset.fit_gaussians()

end_time = time.time()
script_duration = end_time - start_time
print(f"Script execution time: {script_duration:.3f} seconds.")
