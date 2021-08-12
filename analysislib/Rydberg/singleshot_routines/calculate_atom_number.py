from lyse import path, routine_storage
from analysislib.Rydberg.analysis_utils.data_classes import Shot

# Get the Run instance with all of the shot's acquired data, such as
# images, traces, and results from analysis.
shot = Shot(path)

# image with atoms + imaging beam
atoms_image = shot.get_image('basler', 'CMOT', 'atoms')
# image without atoms + imaging beam
no_atoms_image = shot.get_image('basler', 'CMOT', 'no_atoms')
# optionally can include an image that has none of the above (a background image) and pass this to process_image as well

shot.process_image(atoms_image, no_atoms_image, plot=True)




