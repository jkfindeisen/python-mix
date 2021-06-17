"""

GUI for the hop scanning RESOLFT measurements with Daniel Stumpf and
Jan Keller-Findeisen at the Dep. NanoBiophotonics, MPI-BPC Göttingen

Note:
    
- Only stacks with exactly 4 dimensions can be create with Measurement.create_stack()

specpy-1.2.3-cp37-cp37m-win_amd64.whl
C:\Imspector\Versions\16.3.13367-w2109-win64\python

"""

import os
import sys
import time
from datetime import datetime
from PyQt5 import QtWidgets, QtCore, QtGui
import numpy as np
import specpy as sp


# TODO how are stacks contents updated in Imspector?
# TODO specpy 1.2.3 description
# TODO color coding of output
# TODO how to know that a stack is still present in Imspector

class MainWindow(QtWidgets.QWidget):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setMinimumSize(800, 600)
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

    def log(self, text):
        """

        :param text:
        :return:
        """
        self._log.append('<font color="gray">[{}]:</font> {}'.format(datetime.now().time(), text))


class Worker(QtCore.QObject):
    """

    """
    log = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()  # signals that the worker has finished the current job

    def __init__(self):
        super().__init__()
        # imspector handle
        self.im = None

    def connect_to_imspector(self):
        """

        :return:
        """
        try:
            self.im = sp.get_application()
            self.log.emit('Connected to Imspector version {} on host {}.'.format(self.im.version(), self.im.host()))
        except Exception as e:
            self.log.emit('Could not connect to Imspector.\n{}'.format(e))

        self.finished.emit()

    def check_settings(self):
        """

        :return:
        """
        if not self.im:
            self.log.emit('Not connected to Imspector.')
            return False

        self.log.emit('Check active measurement.')

        # get active measurement
        try:
            msr = self.im.active_measurement()
        except Exception as e:
            self.log.emit(' Could not obtain active measurement. ({})'.format(e))
            return False

        # get active configuration
        cfg = msr.active_configuration()

        # check that name contains xyc
        if 'xyc' not in cfg.name():
            self.log.emit(' Warning: Active configuration name does not contain "xyc".')

        # check custom axis
        p = cfg.parameters('/')
        if 'CustomAxis' not in p:
            self.log.emit('CustomAxis not in configuration parameters')
            return False
        p2 = cfg.parameters('CustomAxis')

        if p2['enabled'] is not True:
            self.log.emit('Custom axis not enabled, should be enabled.')

        if p2['pve']['value_name']['path'] != 'ExpControl.scan.range.x.off':
            self.log.emit('lkfhkjf')

        length = p2['axis']['len']
        off = p2['axis']['off']
        res = p2['axis']['res']
        psz = p2['axis']['psz']
        self.log.emit('Custom axis {}, {}, {}, {}'.format(length, off, res, psz))

        p2 = cfg.parameters('ExpControl')

        sm = p2['scan']['range']['scanmode']
        sq = p2['scan']['range']['square_pixels']
        self.log.emit('Scan {}, {}'.format(sm, sq))
        self.log.emit(str(p2['scan']['range']['x']))
        self.log.emit(str(p2['scan']['range']['y']))

        return True

    def run_measurement(self):
        """

        :return:
        """
        if not self.im:
            self.log.emit('Not connected to Imspector.')
            return

        # check settings
        if not self.check_settings():
            self.log.emit('Check not passed.')
            return

        # get active measurement
        msr = self.im.active_measurement()

        # run active measurement with timing
        self.log.emit('Active measurement running ...')
        t1 = time.perf_counter()
        self.im.run(msr)
        t2 = time.perf_counter()
        self.log.emit('Finished ({:.2f}s)'.format(t2 - t1))

        # get data out again
        cfg = msr.active_configuration()
        number_stacks = cfg.number_of_stacks()

        # check that there are two stacks
        if number_stacks != 2:
            self.log.emit(' Not exactly two output stacks after measurement. Cannot unhop scans.')
            return

        # get both and unhop
        for idx in range(number_stacks):
            stack = cfg.stack(idx)

            # unhopping
            self.log.emit('Unhopping stack {}.'.format(stack.name()))

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


def load_icon(name):
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
