"""
  Example for the OBF file format reader implementation in obf_support.py. Prints some useful info and shows first
  XY slices of all stacks with at least two dimensions. For a documentation of the API see file obf_support.py itself.
"""

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import obf_support

if __name__ == '__main__':
    # add a path to an ".obf" or ".msr" file here
    file_path = 'path_to_obf_file'

    obf = obf_support.File(file_path)

    print('file: {}'.format(file_path))
    print(' format version: {}'.format(obf.format_version))
    print(' description: "{}"'.format(obf.description))
    print(' contains {} stacks'.format(len(obf.stacks)))

    for index, stack in enumerate(obf.stacks[-1:]):
        print('\nstack {}'.format(index))
        print(' format version: {}'.format(stack.format_version))
        print(' name: "{}"'.format(stack.name))
        print(' description: "{}"'.format(stack.description))
        print(' shape: {}'.format(stack.shape))
        print(' dimensionality: {}'.format(stack.dimensionality))
        print(' lengths: {}'.format(stack.lengths))
        print(' pixel sizes: {}'.format(stack.pixel_sizes))
        print(' offsets: {}'.format(stack.offsets))
        print(' data type: {}'.format(stack.data_type.__name__))

        # load stack data and show first 2D image
        data = stack.data
        if data.size > 0:  # don't display empty stacks
            fig, ax = plt.subplots()
            idx = [slice(None), slice(None)] + [0] * (len(data.shape) - 2)
            im = ax.imshow(data[tuple(idx)].reshape(data.shape[:2]), cmap=cm.hot)
            ax.set_title(stack.name)

        plt.show()
