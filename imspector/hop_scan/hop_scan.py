"""
GUI for the hop scanning RESOLFT measurements with Daniel Stumpf and
Jan Keller-Findeisen at the Dep. NanoBiophotonics, MPI-BPC Göttingen

The Hop scanning measurements using the Imspector software from Aberrior Instruments (AI) use
large step sizes in the first scan axis and a custom axis with a gradual shift in offset to achieve
hop scanning. The hop scan is necessary to allow switchable proteins to return to their ground state.

Implementation notes:

- Currently runs together with Imspector 16.3.13367-w2109-win64
- Uses specpy-1.2.3-cp37-cp37m-win_amd64.whl in Python 3.7 environment (Conda)
- Only stacks with exactly 4 dimensions can be created with Measurement.create_stack() in specpy
- Imspector does not get notified if stack contents are updated within specpy, the colorbar scaling is wrong
- There is no description of SpecPy 1.2.3 available (used the one from 1.2.1 at https://pypi.org/project/specpy/)
- There are small changes in the usage, could write a document here about them.
- If a stack on the Imspector side is closed, there is no way to know from Python about that.

  Author: Jan Keller-Findeisen (https://github.com/jkfindeisen), June 2021, MIT licensed (see LICENSE)
"""

import os
import sys
import time
from datetime import datetime
from PyQt5 import QtWidgets, QtCore, QtGui
import numpy as np
import specpy as sp

# TODO should we maybe override the created stacks next time around or create new every time?
# TODO in principle we also could connect to an Imspector at another location, is this interesting, would specpy Stack creation still work? (I guess not)
# TODO general all checks for equality should take numerical precision into account, i.e. instead of a==b do abs(a-b) < 1e-3*(abs(a)+abs(b)) or similar
# TODO if there are more than two stacks to unhop, try to unhop them all (check for nunmber of stacks)

class MainWindow(QtWidgets.QWidget):
    """
    Main window of the GUI. Just does the layout and connects the buttons with their functions.
    The work is done with a worker thread, which executes methods on the worker. We communicate with the
    worker thread with signals.
    """

    def __init__(self, *args, **kwargs):
        """
        Sets up the layout of the main window.
        """
        super().__init__(*args, **kwargs)

        self.setMinimumSize(900, 700)
        self.setWindowTitle('Hop scanning in Imspector')

        # worker setup
        self._worker = Worker()
        self._worker_thread = QtCore.QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.start()

        # connecting worker
        self._worker.log.connect(self.log)


        # log output
        self._log = QtWidgets.QTextEdit(self)
        self._log.setReadOnly(True)
        self._log.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._log.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        font = self._log.font()
        font.setPointSizeF(font.pointSizeF()+2)
        self._log.setFont(font)

        # tool bar
        toolbar = QtWidgets.QToolBar(self)

        # connect action
        action = QtWidgets.QAction(load_icon('link'), 'Connect to Imspector', self)
        action.triggered.connect(self._worker.connect_to_imspector)
        toolbar.addAction(action)

        # check action
        action = QtWidgets.QAction(load_icon('fact_check'), 'Check measurement configuration', self)
        action.triggered.connect(self._worker.check_settings)
        toolbar.addAction(action)

        # run measurement action
        action = QtWidgets.QAction(load_icon('play_arrow'), 'Run measurement and unhop', self)
        action.triggered.connect(self._worker.run_measurement)
        toolbar.addAction(action)

        # spacer
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        toolbar.addWidget(spacer)

        # help action
        action = QtWidgets.QAction(load_icon('help_center'), 'Show further information', self)
        action.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl('https://github.com/jkfindeisen/python-mix/blob/main/imspector/hop_scan/README.md')))
        toolbar.addAction(action)

        # layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(toolbar)
        layout.addWidget(self._log)

    def log(self, text: str, type: int=0):
        """
        Appends a message to the log window prefixing it with the time and possible with different colors.
        :param text: The message to display.
        :param type: An integer indicating the color of the text (see dictionary below).
        """
        colors = {0: 'black', 1: 'red', 2: 'green', 3: 'magenta'}
        color = colors[type]
        self._log.append('<font color="gray">[{}]:</font> <font color="{}">{}</font>'.format(datetime.now().time().isoformat()[:-5], color, text))  # lazy with the time format (just killing 5 decimal places here)
        
    def closeEvent(self, event):
        """
        Makes sure that the worker thread has finished (and finishes its business before) before closing the window.
        """
        self._worker_thread.quit()
        self._worker_thread.wait()


class Worker(QtCore.QObject):
    """
    The worker class which does all the interfacing with Imspector and is executed within a worker thread. It communicates
    with the GUI via signals and slots.
    """
    log = QtCore.pyqtSignal(str, int)

    def __init__(self):
        """
        Initially there is no Imspector connection.
        """
        super().__init__()
        # Imspector handle
        self.im = None

    def connect_to_imspector(self):
        """
        Tries to establish an Imspector connection and logs the result.
        """
        self.log.emit('Connecting with local Imspector.', 0)
        try:
            self.im = sp.get_application()
            self.log.emit('Connected to Imspector version {} on host {}.'.format(self.im.version(), self.im.host()), 0)
        except Exception as e:
            self.log.emit(str(e), 1)

    def check_settings(self) -> bool:
        """
        Checks the settings of the current active measurement (hop scan) for plausibility and return False if the check
        failed.
        :return: True if the check is passed, False if it failed.
        """
        if not self.im:
            self.log.emit('Not connected to Imspector.', 1)
            return False

        self.log.emit('Check active measurement.', 0)

        # get active measurement
        try:
            msr = self.im.active_measurement()
        except Exception as e:
            self.log.emit(' Could not obtain active measurement. ({})'.format(e), 1)
            return False

        # get active configuration
        cfg = msr.active_configuration()

        # check that name contains xyc
        if 'xyc' not in cfg.name():
            self.log.emit(' Warning: Active configuration name does not contain "xyc".', 3)

        # check custom axis
        p = cfg.parameters('/')
        if 'CustomAxis' not in p:
            self.log.emit('CustomAxis not in configuration parameters', 1)
            return False
        pA = cfg.parameters('CustomAxis')

        if pA['enabled'] is not True:
            self.log.emit('Custom axis not enabled, should be enabled.', 1)
            return False

        if pA['pve']['value_name']['path'] != 'ExpControl.scan.range.x.off':
            self.log.emit('Custom axis type is not "ExpControl.scan.range.x.off".', 1)
            return False

        length = pA['axis']['len']
        offset = pA['axis']['off']
        resolution = pA['axis']['res']
        pixel_size = pA['axis']['psz']
        self.log.emit('Custom axis: length: {}, offset: {}, resolution: {}, pixel size: {}'.format(length, offset, resolution, pixel_size), 2)

        pS = cfg.parameters('ExpControl')

        scan_mode = pS['scan']['range']['scanmode']
        square_pixels = pS['scan']['range']['square_pixels']

        self.log.emit('Scan range type {} and square pixels: {}'.format(scan_mode, square_pixels), 2)
        if square_pixels:
            self.log.emit("Warning: Most probably there shouldn't be square pixels.", 1)
        
        for axis in ['x', 'y']:
            ax = pS['scan']['range'][axis]
            length = ax['len']
            offset = ax['off']
            resolution = ax['res']
            üixel_size = ax['psz']
            self.log.emit('Axis {}: length: {}, offset: {}, resolution: {}, pixel size: {}:'.format(axis, length, offset, resolution, pixel_size), 2)
            
        # check consistency
        
        # x axis length of length of custom axis
        x_px = pS['scan']['range']['x']['psz']
        ca_eff_len = pA['axis']['res'] *  pA['axis']['psz']
        if (x_px - ca_eff_len) / (x_px + ca_eff_len) > 0.01:
            self.log.emit('Pixel hop size {} in x does not match effective length of custom axis {}, adjust.'.format(x_px, ca_eff_len), 1)
            return False
        
        # pixel size along custom axis and along y axis
        y_px = pS['scan']['range']['y']['psz']
        ca_px = pA['axis']['psz']
        if y_px != ca_px:
            self.log.emit('Warning: pixel size in y {} does not equal pixel size along custom axis (no eff. square pixels). Intended?'.format(y_px, ca_px), 3)
        
        return True

    def run_measurement(self):
        """
        Checks and runs the hop scanning measurement. Times it also and afterwards unhop the scan, creating
        two new stacks in the current active measurement.
        """
        if not self.im:
            self.log.emit('Not connected to Imspector.', 1)
            return

        # check settings
        if not self.check_settings():
            self.log.emit('Check not passed.', 1)
            return

        # get active measurement
        msr = self.im.active_measurement()

        # run active measurement with timing
        self.log.emit('Active measurement running ...', 0)
        t1 = time.perf_counter()
        self.im.run(msr)
        t2 = time.perf_counter()
        self.log.emit('Finished ({:.2f}s)'.format(t2 - t1), 2)

        # get data out again
        cfg = msr.active_configuration()
        number_stacks = cfg.number_of_stacks()

        # check that there are two stacks
        if number_stacks != 2:
            self.log.emit('Not exactly two output stacks after measurement. Cannot unhop scans.', 1)
            return

        # get both and unhop
        for idx in range(number_stacks):
            stack = cfg.stack(idx)

            # unhopping
            self.log.emit('Unhopping stack {}.'.format(stack.name()), 2)

            # get stack data (note: dimensions are reversed to what one would expect)
            data = stack.data()

            # order: T, C, Y, X

            # unhop
            new_data = np.transpose(data, axes=[0, 2, 3, 1])  # T, Y, X, C
            s = new_data.shape
            new_data = np.reshape(new_data, [1, s[0], s[1], s[2] * s[3]])  # None, T, Y, X(full)

            # create output stack
            s = msr.create_stack(stack.type(),
                                 new_data.shape[::-1])  # one has to reserve the order of the dimensions again here
            d = s.data()
            d[:] = new_data[:]
            s.set_name(stack.name() + ' Unhopped')
            s.set_description('config {} stack {} unhopped'.format(cfg.name(), stack.name()))

            # fix lengths, offsets, labels
            lengths = stack.lengths()
            lengths[2] = lengths[3]
            lengths[3] = 1.0
            s.set_lengths(lengths)

            offsets = stack.offsets()
            offsets[2] = offsets[3]
            offsets[3] = -0.5
            s.set_offsets(offsets)

            labels = stack.labels()
            labels[2] = labels[3]
            labels[3] = 'None'
            s.set_labels(labels)

        msr.update()  # does this tell Imspector to update the colorbar ranges of the pushed stacks?


def load_icon(name: str) -> QtGui.QIcon:
    """
    Loads an icon (as QIcon) from our resources place.
    :param name: Just the name part from the icon file.
    :return: The QIcon.
    """
    path = os.path.join(root_path, 'resources', 'icon_' + name + '.png')
    icon = QtGui.QIcon(path)
    return icon


def exception_hook(type, value, traceback):
    """
    Use sys.__excepthook__, the standard hook.
    """
    sys.__excepthook__(type, value, traceback)


if __name__ == '__main__':

    # fix PyQt5 eating exceptions (see http://stackoverflow.com/q/14493081/1536976)
    sys.excepthook = exception_hook

    # root path is file path
    root_path = os.path.dirname(__file__)

    # create app
    app = QtWidgets.QApplication([])
    app.setWindowIcon(load_icon('breakdance'))

    # show main window
    window = MainWindow()
    window.show()
    window.log('Using specpy version {}.'.format(sp.version.__version__))

    # start Qt app execution
    sys.exit(app.exec_())
