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
    print('file format version: {}'.format(obf.format_version))
    print('file description: "{}"'.format(obf.description))
    print('contains {} stacks'.format(len(obf.stacks)))

    for stack in obf.stacks:
        print('\nstack format version: {}'.format(stack.format_version))
        print('stack name: "{}"'.format(stack.name))
        print('stack description: "{}"'.format(stack.description))
        print('stack shape: {}'.format(stack.shape))
        print('stack lengths: {}'.format(stack.lengths))
        print('stack pixel sizes: {}'.format(stack.pixel_sizes))
        print('stack offsets: {}'.format(stack.offsets))
        print('stack data type: {}'.format(stack.data_type.__name__))

        # load stack data and show first 2D image
        data = stack.data
        fig, ax = plt.subplots()
        idx = [slice(None), slice(None)] + [0] * (len(data.shape) - 2)
        im = ax.imshow(data[tuple(idx)].reshape(data.shape[:2]), cmap=cm.hot)
        ax.set_title(stack.name)

        plt.show()
