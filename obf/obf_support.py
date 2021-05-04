"""
  Pure Python read only support for OBF files. The OBF file format originates from the Department of NanoBiophotonics
  of the Max Planck Institute for Biophysical Chemistry in Göttingen, Germany. A specification can be found at
  https://github.com/AbberiorInstruments/ImspectorDocs/blob/master/docs/fileformat.rst This implementation is similar
  to the File and Stack API of specpy (https://pypi.org/project/specpy/). Can also read MSR files (the OBF part of it).

  Documentation:

  - Import with "import obf_support"

  File
  - Open an OBF file with "obf = obf_support.File(path_to_file)", that will read all meta data (including stack meta data)
  - Access the following attributes: format_version, description, stacks
  - Close with "obf.close()" (optional, is also closed automatically on deletion of the File object)

  Stacks
  - Stacks is a list of all contained stacks
  - Each Stack has attributes: format_version, name, description, shape, lengths, offsets, data_type, data
  - data returns a NumPy array containing the stack data (the stack data is loaded from the file lazily, i.e. when the
    attributes is accessed the first time)

  Example: see obf_support_example.py

  Implementation notes:

  - Relies on the struct module (https://docs.python.org/3.9/library/struct.html).
  - Constant OMAS_BF_MAX_DIMENSIONS is not explained, the value is 15.
  - Data type OMAS_DT is not specified, it's an enum type in C++, which is stored as uint32.
  - Writing to OBF would in principle be possible (using the struct module), but not intended currently
  - TODO: Read part of data, currently data is read all at once (impractical for very large files)
  - TODO: data_len_disk not yet taken into account, will crash if not all data is written
  - TODO: Read stack footers and read data that was stored in chunks (stack file format version 6)
  - TODO: not tested a lot

  Author: Jan Keller-Findeisen (https://github.com/jkfindeisen), May 2021
"""

# TODO add type hints, run lint
# TODO add license information

import struct
import zlib
import numpy as np

# file header - char[10], uint32, uint64, uint32
file_header_fmt = '<10sIQI'
file_header_len = struct.calcsize(file_header_fmt)
file_header_unpack = struct.Struct(file_header_fmt).unpack_from
FILE_MAGIC_HEADER = b'OMAS_BF\n\xff\xff'

# stack header - char[16], uint32, uint32, uint32[15], double[15], double[15], uint32, uint32, uint32, uint32, uint32, uint64, uint64, uint64
stack_header_fmt = '<16s17I30d5I3Q'
stack_header_len = struct.calcsize(stack_header_fmt)
stack_header_unpack = struct.Struct(stack_header_fmt).unpack_from
STACK_MAGIC_HEADER = b'OMAS_BF_STACK\n\xff\xff'

# stack footer

# mapping of OMAS_DT to NumPy data types
omas_data_types = {1: np.uint8, 2: np.int8, 4: np.uint16, 8: np.int16, 16: np.uint32, 32: np.int32, 64: np.float32,
                   128: np.float64}


class File:
    """
    OBF file access.

    Create a new OBF file access object by providing a file path:
    obf = File(file_path)
    """

    def __init__(self, file_path):
        """

        :param file_path:
        """
        # we cannot use "with open as" because we read the data stacks content later
        try:
            # open the file at the given file path
            self._file = open(file_path, 'rb')

            # read the obf file header
            data = self._file.read(file_header_len)
            magic_header, self.format_version, first_stack_pos, description_len = file_header_unpack(data)
            if magic_header != FILE_MAGIC_HEADER:
                raise RuntimeError('Magic file header not found.')

            # read file description
            self.description = self._read_string(description_len)

            # read all the stacks
            next_stack_pos = first_stack_pos
            self.stacks = []
            while next_stack_pos != 0:

                # seek to position of next stack header
                self._file.seek(next_stack_pos)

                # read stack header
                data = self._file.read(stack_header_len)
                values = stack_header_unpack(data)
                if values[0] != STACK_MAGIC_HEADER:
                    raise RuntimeError('Magic stack header not found.')

                # interpret stack header
                format_version = values[1]
                rank = values[2]
                shape = values[3:17][:rank]
                lengths = values[18:32][:rank]
                offsets = values[33:47][:rank]
                data_type = values[48]
                if data_type not in omas_data_types:
                    raise RuntimeError('Unsupported data type.')
                else:
                    data_type = omas_data_types[data_type]
                compression_type = values[49]
                # compression_level = values[50] # relatively uninteresting
                name_length = values[51]
                description_length = values[52]
                data_length = values[54]
                next_stack_pos = values[55]
                name = self._read_string(name_length)
                description = self._read_string(description_length)

                data_pos = self._file.tell()

                # create new stack
                stack = Stack(self, format_version, name, description, shape, lengths, offsets, data_type,
                              compression_type, data_pos, data_length)
                self.stacks.append(stack)
        except:
            self.close()
            raise

    def find_stack_by_name(self, string):
        """
        Small convenience method. Will return all stacks in this OBF file where string is contained in the stack name.
        """
        return [stack for stack in self.stacks if string in stack.name]

    def close(self):
        """
        Closes the file if it isn't closed already.
        """
        if not self._file.closed:
            self._file.close()

    def _read_string(self, length):
        """
        For internal use only.
        :param length:
        :return:
        """
        try:
            data = self._file.read(length)
            fmt = '<{}s'.format(length)
            string = struct.unpack_from(fmt, data)[0]  # unpack_from always returns a tuple
            string = string.decode('utf-8')
            return string
        except:
            self.close()
            raise

    def _read_stack(self, stack):
        """
        Internal function. Reads the data array from a stack from the OBF file as a NumPy array and stores it as the
        data attribute of the stack.
        :param stack:
        :return:
        """
        try:
            # read the whole stack data
            self._file.seek(stack._data_pos)
            data = self._file.read(stack._data_length)

            # if compressed, uncompress
            if stack._compression_type == 1:
                data = zlib.decompress(data)

            # convert to numpy array
            array = np.frombuffer(data, dtype=np.int16)

            # reshape (with reversed shape and then reverse order of dimensions)
            array = np.reshape(array, stack.shape[::-1])
            array = np.transpose(array)

            # store
            stack._data = array
        except:
            self.close()
            raise

    def __del__(self):
        """
        Make sure that the file is closed upon deletion.
        """
        self.close()


class Stack:
    """

    """

    def __init__(self, obf, format_version, name, description, shape, lengths, offsets, data_type, compression_type, data_pos, data_length):
        """

        :param obf:
        :param format_version:
        :param name:
        :param description:
        :param shape:
        :param lengths:
        :param offsets:
        :param data_type:
        :param compression_type:
        :param data_pos:
        :param data_length:
        """
        self.obf = obf
        self.format_version = format_version
        self.name = name
        self.description = description
        self.shape = shape
        self.lengths = lengths
        self.offsets = offsets
        self.data_type = data_type
        self._compression_type = compression_type
        self._data_pos = data_pos
        self._data_length = data_length
        self._data = None

    def __getattr__(self, name):
        """
        Computes a few convenience attributes on the fly as well as lazy loading of the data
        :param name:
        :return:
        """
        if name == 'pixel_sizes':
            pixel_sizes = [l / n for n, l in zip(self.shape, self.lengths)]
            return pixel_sizes
        elif name == 'data':
            if self._data is None:
                # first time data is called, load it
                self.obf._read_stack(self)
            return self._data
