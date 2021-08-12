import numpy as np

from lyse import Run, data, path, routine_storage
from analysislib.Rydberg.analysis_utils.absorption_image_processor import AbsorptionImageProcessor
from analysislib.Rydberg.analysis_utils.data_classes import Shot

# Get the pandas series with all of the globals etc. for this shot.
ser = data(path)

# Create an instance of our custom Shot class. This class inherits from lyse.Run
# so it has all of that class's methods and more, and so it can be used in place
# of the lyse.Run class.
shot = Shot(path)

# Set options for when an AbsorptionImageProcessor instance is created.
max_beam_images = ser['on_the_fly_max_beam_images']
max_principal_components = ser['on_the_fly_max_principal_components']
use_sparse_routines = False


# Make function for creating a new AbsorptionImageProcessor since there are a
# few spots below where we may need to do that.
def create_new_absorption_image_processor():
    processor = AbsorptionImageProcessor(
        max_beam_images=max_beam_images,
        max_principal_components=max_principal_components,
        use_sparse_routines=use_sparse_routines,
    )
    routine_storage.on_the_fly_absorption_image_processor = processor
    return processor


# Getting the processor from Lyse's routine_storage keeps it alive between runs
# of this script, which makes it possible to keep background images from
# previous shots.
# Create a new absorption image processor if we don't have one going already.
if not hasattr(routine_storage, 'on_the_fly_absorption_image_processor'):
    processor = create_new_absorption_image_processor()

# Get the absorption image processor.
processor = routine_storage.on_the_fly_absorption_image_processor

# Create a new processor if we want a different value for max_beam_images.
if processor.max_beam_images != max_beam_images:
    processor = create_new_absorption_image_processor()

# Ensure processor has desired value for max_principal_components.
processor.max_principal_components = max_principal_components

# Add the beam image to the processor.
try:
    processor.add_beam_image(shot)
except ValueError:
    # Image shape has changed, can't use old beam_images anymore. We'll create a
    # new on_the_fly_absorption_image_processor.
    processor = create_new_absorption_image_processor()
    processor.add_beam_image(shot)

# Make mask for atom region.
atom_region_rows = ser['atom_region_rows']
atom_region_cols = ser['atom_region_cols']
processor.set_rectangular_mask(atom_region_rows, atom_region_cols)

# Do the analysis on the image.
shot.process_image(processor)
