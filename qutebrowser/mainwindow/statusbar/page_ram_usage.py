"""Page RAM usage displayed in the statusbar."""

import platform
from qutebrowser.browser import browsertab
from qutebrowser.misc import throttle
from qutebrowser.qt.core import Qt

from qutebrowser.mainwindow.statusbar import textbase
from qutebrowser.utils import usertypes
from qutebrowser.utils import log


class PageRamUsage(textbase.TextBase):
    """Show memory usage of the renderer process"""

    @staticmethod
    def __mem_usage_darwin(pid: int) -> str:
        return "not implemented"

    @staticmethod
    def __mem_usage_windows(pid: int) -> str:
        return "not implemented"

    @staticmethod
    def __mem_usage_linux(pid: int) -> str:
        _proc_status = f'/proc/{pid}/status'
        _scale = {'kB': 1024.0, 'mB': 1024.0*1024.0, 'KB': 1024.0, 'MB': 1024.0*1024.0}

        def _VmB(VmKey):
            '''Private.'''
            # get pseudo file  /proc/<pid>/status
            try:
                t = open(_proc_status)
                v = t.read()
                t.close()
            except Exception:
                log.statusbar.exception(f"failed to open {_proc_status} file")
                return 0.0  # non-Linux?
            # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
            i = v.index(VmKey)
            v = v[i:].split(None, 3)  # whitespace
            if len(v) < 3:
                return 0.0  # invalid format?
            # convert Vm value to bytes
            return float(v[1]) * _scale[v[2]]

        def memory(since=0.0):
            '''Return memory usage in bytes.'''
            return _VmB('VmData:') - since

        def resident(since=0.0):
            '''Return resident memory usage in bytes.'''
            return _VmB('VmRSS:') - since

        def stacksize(since=0.0):
            '''Return stack size in bytes.'''
            return _VmB('VmStk:') - since

        mem = resident() / _scale["mB"]
        return "%.2f" % mem

    UPDATE_DELAY = 1000  # ms

    def __init__(self, parent=None):
        super().__init__(parent, elidemode=Qt.TextElideMode.ElideNone)
        self._set_text = throttle.Throttle(self.setText, 100, parent=self)
        self.timer = usertypes.Timer(self)
        self.timer.timeout.connect(self._show_ram_usage)
        self.pid = 0

    def _show_ram_usage(self):
        """Set text to current time, using self.format as format-string."""
        usage = "N/A"
        try:
            if self.pid == 0:
                return
            dct = {
                "Linux": PageRamUsage.__mem_usage_linux,
                "Darwin": PageRamUsage.__mem_usage_darwin,
                "Windows": PageRamUsage.__mem_usage_windows,
            }
            sys = platform.system()
            if sys in dct:
                usage = dct[sys](self.pid)
            else:
                log.statusbar.warning(f"unknown platform {sys}")
        except Exception:
            log.statusbar.exception("failed to get page ram usage")
        self._set_text(f"RAM: {usage} MB")

    def on_tab_changed(self, tab: browsertab.AbstractTab):
        """Update page ram usage if possible"""
        try:
            self.pid = tab.pid()
            self._show_ram_usage()
        except Exception:
            """we can catch ErrNotImplemented here because tab.pid() implemented only
            for qtwebengine"""
            log.statusbar.exception("failed to get tab pid or show ram usage")

    def hideEvent(self, event):
        """Stop timer when widget is hidden."""
        self.timer.stop()
        super().hideEvent(event)

    def showEvent(self, event):
        """Override showEvent to show time and start self.timer for updating."""
        self.timer.start(PageRamUsage.UPDATE_DELAY)
        self._show_ram_usage()
        super().showEvent(event)
