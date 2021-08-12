import matplotlib.pyplot as plt
import numpy as np

from lyse import Run, data, path
from matplotlib.widgets  import RectangleSelector

# Get the pandas series with all of the globals etc. for this shot
ser = data(path)

# Get the Run instance with all of the shot's acquired data, such as
# images, traces, and results from analysis.
run = Run(path)

atoms_image = run.get_image('basler', 'CMOT', 'atoms')

# plt.figure()
# plt.title('Atoms Image')
# plt.imshow(atoms_image, cmap=plt.get_cmap('jet'))
# plt.colorbar()

no_atoms_image = run.get_image('basler', 'CMOT', 'no_atoms')

# plt.figure()
# plt.title('No Atoms Image')
# plt.imshow(no_atoms_image, cmap=plt.get_cmap('jet'))
# plt.colorbar()

divided_image = atoms_image/no_atoms_image
plt.figure()
plt.title('Divided Image')
plt.imshow(divided_image, cmap=plt.get_cmap('jet'))
plt.colorbar()
print(f"Peak bin count in atom image is {np.amax(atoms_image)}")
plt.tight_layout()


