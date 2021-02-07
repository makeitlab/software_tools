""" 
Serial Flow Monitor (SFMonitor) - Serial port monitor for robotic purposes.
Version: 1.2
Home page: www.poprobot.ru/soft/sfmonitor

Oleg Evsegneev (oleg.evsegneev@gmail.com)
Last modified: 06.10.2015

Author of original conception:
Eli Bendersky (eliben@gmail.com)
"""
import random, sys, configparser, queue, gettext
from PyQt4.QtCore import *
from PyQt4.QtGui import * 
import serial
import pyqtgraph as pg
from formlayout import fedit

from com_monitor import ComMonitorThread, FMT_SIMPLE, FMT_COMPLEX_VT, FMT_COMPLEX_YX
from utils import *


BUFFER_SIZE = 20
BUFFER_ALARM = 15

PACKET_SIZE = 3
VALUE_SIZE = 1
SEPARATOR = False

_baud_rates = ('110', '300', '600', '1200', '2400', '4800',
               '9600', '14400', '19200', '38400', '57600',
               '115200', '230400', '460800', '921600')
_langs = {'English':'en','Russian':'ru'}
_langsi = {'en':'English','ru':'Russian'}

class PlottingDataMonitor(QMainWindow):

    port_name = 0
    port_name_opened = None
    baud_rate = 0
    lang = 'en'
    status = ''
    data = [0,0,0]
    
    def __init__(self, parent=None):
        super(PlottingDataMonitor, self).__init__(parent)
        
        self.monitor_active = False
        self.com_monitor = None
        self.com_data_q = None
        self.com_error_q = None

        self.timer = QTimer()
        
        self.load_config()

        self.create_menu()
        self.create_main_frame()
        self.create_status_bar()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, _('Exit'),
            _('Are you sure to quit?'), QMessageBox.Yes | 
            QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.save_config();
            event.accept()
        else:
            event.ignore()

    def load_config(self):
        self.config = configparser.ConfigParser()
        self.config.read('settings.cfg')
        cget = self.config.get

        try:
            self.lang = cget('Common', 'lang')
        except:
            self.lang = DEFAULT_LANG
    
        # Baud rate
        try:
            self.baud_rate = int(cget('Port', 'baud_rate'))
        except:
            self.baud_rate = DEFAULT_BAUD_RATE

        # Port name
        value = cget('Port', 'name', fallback=None)
        if self.check_port(value):
            self.port_name = value

    def save_config(self):
        self.config = configparser.ConfigParser()
        cset = self.config.set
        csec = self.config.add_section

        # Common preferences
        csec('Common')
        cset('Common', 'lang', self.lang)
        
        # Port
        csec('Port')
        cset('Port', 'baud_rate', str(self.baud_rate))
        cset('Port', 'name', self.port_name or '')
        
        with open('settings.cfg', 'w') as configfile:
            self.config.write(configfile)
    
    def create_info_box(self, name, length=15):
        label = QLabel(name)
        edit = QLineEdit()
        edit.setEnabled(False)
        edit.setFrame(False)
        edit.setMaxLength(length)        
        return (label, edit)

    def create_checkbox(self, title):
        cb = QCheckBox(title, self)
        cb.toggle()
        return cb

    def create_status_bar(self):
        self.status = 'Monitor idle'
        self.status_text = QLabel(_(self.status))
        self.statusBar().addWidget(self.status_text, 1)
    
    def create_main_frame(self):
        # COM port control
        #
        port_layout = QHBoxLayout()
        
        # port name
        self.portname_l, self.portname_ = self.create_info_box(_('Port name:'), 15)
        if self.port_name and self.baud_rate:
            self.portname_.setText('%s (%s)' % (self.port_name, _baud_rates[self.baud_rate]))
        
        port_layout.addWidget(self.portname_l)
        port_layout.addWidget(self.portname_, 0)

        # control buttons
        self.selport_btn = QPushButton(_("Select"))
        self.selport_btn.clicked.connect(self.on_select_port)
        self.start_btn = QPushButton(_("Start"))
        self.start_btn.clicked.connect(self.on_start)
        self.stop_btn = QPushButton(_("Stop"))
        self.stop_btn.clicked.connect(self.on_stop)
        self.break_btn = QPushButton(_("Break port"))
        self.break_btn.clicked.connect(self.on_break)
        self.reset_btn = QPushButton(_("Reset"))
        self.reset_btn.clicked.connect(self.on_reset)
        
        port_layout.addWidget(self.selport_btn)
        port_layout.addWidget(self.start_btn)
        port_layout.addWidget(self.stop_btn)
        port_layout.addWidget(self.break_btn)
        port_layout.addWidget(self.reset_btn)
        port_layout.addStretch(1)
        
        self.port_groupbox = QGroupBox(_('COM port'))
        self.port_groupbox.setLayout(port_layout)

        #labels
        f = QFont( "Ubuntu", 80, QFont.Bold)
        vbox = QVBoxLayout()

        #station
        self.main_frame = QWidget()
        label_1t = QLabel()
        label_1t.setText(_("Station")+": ")
        label_1t.setFont(f)
        label_1t.setAlignment(Qt.AlignLeft)
        self.label_1 = QLabel()
        self.label_1.setText("--")
        self.label_1.setFont(f)
        self.label_1.setAlignment(Qt.AlignLeft)

        hbox = QHBoxLayout()
        hbox.addWidget(label_1t)
        hbox.addWidget(self.label_1)
        #label_1t.setFixedSize(800,200)

        vbox.addLayout(hbox)
        vbox.addSpacing(100)

        #temperature
        self.main_frame = QWidget()
        label_2t = QLabel()
        label_2t.setText(_("Radiation")+": ")
        label_2t.setFont(f)
        label_2t.setAlignment(Qt.AlignLeft)
        self.label_2 = QLabel()
        self.label_2.setText("--")
        self.label_2.setFont(f)
        self.label_2.setAlignment(Qt.AlignLeft)

        hbox = QHBoxLayout()
        hbox.addWidget(label_2t)
        hbox.addWidget(self.label_2)

        vbox.addLayout(hbox)
        vbox.addSpacing(100)

        #radiation
        self.main_frame = QWidget()
        label_3t = QLabel()
        label_3t.setText(_("Temperature")+": ")
        label_3t.setFont(f)
        label_3t.setAlignment(Qt.AlignLeft)
        self.label_3 = QLabel()
        self.label_3.setText("--")
        self.label_3.setFont(f)
        self.label_3.setAlignment(Qt.AlignLeft)

        hbox = QHBoxLayout()
        hbox.addWidget(label_3t)
        hbox.addWidget(self.label_3)

        vbox.addLayout(hbox)

        # Main frame and layout
        #
        self.main_frame = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.port_groupbox)
        main_layout.addStretch(1)
        main_layout.addLayout(vbox)
        self.main_frame.setLayout(main_layout)
        
        self.setCentralWidget(self.main_frame)
        self.set_actions_enable_state()
        #self.create_items()

    def create_menu(self):
        # file menu
        print ('ok')
        self.file_menu = self.menuBar().addMenu(_("File"))
        print ('o1')
        self.selectport_action = self.create_action(_("Select COM port"), slot=self.on_select_port)
        self.start_action = self.create_action(_("Start monitor"), slot=self.on_start)
        self.stop_action = self.create_action(_("Stop monitor"), slot=self.on_stop)
        self.prefs_action = self.create_action(_("Preferences"), slot=self.on_prefs)
        self.exit_action = self.create_action(_("Exit"), slot=self.close)
        
        self.start_action.setEnabled(False)
        self.stop_action.setEnabled(False)
        
        self.add_actions(self.file_menu, (self.selectport_action, self.start_action,
                                          self.stop_action, None, self.prefs_action,
                                          None, self.exit_action))

        # help menu
        self.help_menu = self.menuBar().addMenu(_("Help"))
        self.about_action = self.create_action(_("About"), slot=self.on_about)
        self.manual_action = self.create_action(_("Manual"), shortcut='F1', slot=self.on_manual)
        
        self.add_actions(self.help_menu, (self.about_action, self.manual_action))

    def set_actions_enable_state(self):
        if self.check_port(self.port_name) and self.baud_rate:
            start_enable = not self.monitor_active
            stop_enable = self.monitor_active
        else:
            start_enable = stop_enable = False
        
        self.start_action.setEnabled(start_enable)
        self.start_btn.setEnabled(start_enable)
        self.reset_btn.setEnabled(start_enable)
        self.break_btn.setEnabled(start_enable)
        
        self.stop_action.setEnabled(stop_enable)
        self.stop_btn.setEnabled(stop_enable)

    def on_about(self):
        msg = _('Serial Flow Monitor (SFMonitor) - Serial port monitor for robotic purposes.')+'\n'
        msg += _('Version') + ': 1.2\n'
        msg += _('Home page') + ': www.poprobot.ru/soft/sfmonitor\n'
        msg += _('Online manual') + ': robotclass.ru\n'
        msg += _('Source repository') + ': github.com/makeitlab/software_tools/tree/master/SFMonitor\n'
        msg += _('Author') + ': Oleg Evsegneev (oleg.evsegneev@gmail.com)\n'
        msg += _('Original concept') + ': Eli Bendersky (eliben@gmail.com)\n'
        QMessageBox.about(self, _("About the SFMonitor"), msg)

    def on_manual(self):
        msg = _('Protocol specification')+'\n'
        msg += _('begin data_1 [separator] data_2 ... data_N end')+'\n'
        msg += _('- begin: 0x12')+'\n'
        msg += _('- end: 0x13')+'\n'
        msg += _('- escape: 0x7D')+'\n'
        msg += _('- separator (optional): 0x10')+'\n\n'
        msg += _('Data size: 1, 2 or 4 bytes')+'\n\n'
        msg += _('Example packet: two 16bit numbers 5 and 758, with separator')+':\n'
        msg += _('0x12 0x00 0x05 0x10 0x02 0xF6 0x13')
        QMessageBox.about(self, _("Protocol manual"), msg)

    def on_select_port(self):
        ports = list(enumerate_serial_ports())
        if len(ports) == 0:
            QMessageBox.critical(self, _('I/O Error'),
                _('No serial ports found'))
            return

        datalist = [(_('Port'), [self.port_name or ports[0]]+ports),
                    (_('Baud rate'), (_baud_rates[self.baud_rate],)+_baud_rates),
                    ]

        results = fedit(datalist, title=_("Select COM port"))

        if results:
            self.port_name = results[0]
            self.baud_rate = _baud_rates.index(results[1])
            self.portname_.setText('%s (%s)' % (results[0], results[1]))
            self.set_actions_enable_state()

    def on_stop(self):
        """ Stop the monitor
        """
        if self.com_monitor is not None:
            self.com_monitor.join(0.01)
            self.com_monitor = None

        self.monitor_active = False
        self.timer.stop()
        self.set_actions_enable_state()
        self.port_name_opened = None

        self.status = 'Monitor idle'
        self.status_text.setText(_( self.status))
    
    def on_start(self):
        """ Start the monitor: com_monitor thread and the update
            timer
        """
        if self.com_monitor is not None or self.portname_.text() == '':
            return

        self.reset()
        
        self.data_q = queue.Queue()
        self.error_q = queue.Queue()
        self.com_monitor = ComMonitorThread(
            self.data_q,
            self.error_q,
            full_port_name(self.port_name),
            int(_baud_rates[self.baud_rate]),
            data_format=FMT_COMPLEX_VT,
            value_size=VALUE_SIZE,
            separator=SEPARATOR)
        self.com_monitor.start()

        com_error = get_item_from_queue(self.error_q)
        if com_error is not None:
            QMessageBox.critical(self, _('COM monitor thread error'),
                com_error)
            self.com_monitor = None

        self.port_name_opened = self.port_name
        self.monitor_active = True
        self.set_actions_enable_state()

        self.timer = QTimer()
        self.connect(self.timer, SIGNAL('timeout()'), self.on_timer)

        self.timer.start(100)

        self.status = 'Monitor running'
        self.status_text.setText(_(self.status))

    def on_prefs(self):
        groups = []
        groups.append( ( _('Language'), [_langsi[self.lang]]+[_(l) for l in _langs.keys()] ))

        results = fedit(groups, title=_('Language selection'))
        if results:
            self.lang = _langs[results[0]]
            switch_translator(self.lang)
            self.refresh_texts()
    
    def on_timer(self):
        """ Executed periodically when the monitor update timer
            is fired.
        """
        self.read_serial_data()
        self.update_monitor()

    def on_break(self):
        try:
            serial_port = serial.Serial(port=full_port_name(self.port_name),
                                        baudrate=self.baud_rate,
                                        stopbits=serial.STOPBITS_ONE,
                                        parity=serial.PARITY_NONE,
                                        timeout=0.01)

            serial_port.sendBreak()
            serial_port.close()
        except:
            QMessageBox.critical(self, _('COM port error'),
            _("Can't create serial connection. Try again."))

    def reset(self):
        self.on_reset()

    def on_reset(self):
        pass
        
    def update_monitor(self):
        """ Updates the state of the monitor window with new 
            data. The livefeed is used to find out whether new
            data was received since the last update. If not, 
            nothing is updated.
        """
        self.label_1.setText('%d' % self.data[0])
        self.label_2.setText('%d' % self.data[1])
        self.label_3.setText('%d' % self.data[2])
        
    def read_serial_data(self):
        """ Called periodically by the update timer to read data
            from the serial port.
        """
        qdata = list(get_all_from_queue(self.data_q))
        
        # Simple
        for d in qdata:
            self.data[0] = d[1][0]
            self.data[1] = d[1][1]
            self.data[2] = d[1][2]

    # The following two methods are utilities for simpler creation
    # and assignment of actions
    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(  self, text, slot=None, shortcut=None, 
                        icon=None, tip=None, checkable=False, 
                        signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action

    def check_port( self, name ):
        return name in list(enumerate_serial_ports()) + [self.port_name_opened]

    def refresh_texts( self ):
        self.update_freq_l.setText(_('Update frequency = %s (Hz)') % self.update_freq.value())
        self.status_text.setText(_(self.status))
        self.portname_l.setText(_('Port name:'))
                                                               
        self.freq_groupbox.setTitle(_('Update frequency'))
        self.data_groupbox.setTitle(_('Data'))
        self.port_groupbox.setTitle(_('COM port'))

        #menu
        self.help_menu.setTitle(_('Help'))
        self.about_action.setText(_('About'))
        self.file_menu.setTitle(_('File'))
        self.selectport_action.setText(_('Select COM port'))
        self.start_action.setText(_('Start monitor'))
        self.stop_action.setText(_('Stop monitor'))
        self.prefs_action.setText(_('Preferences'))
        self.exit_action.setText(_('Exit'))

        #buttons
        self.selport_btn.setText(_('Select'))
        self.start_btn.setText(_('Start'))
        self.stop_btn.setText(_('Stop'))
        self.break_btn.setText(_('Break port'))
        self.reset_btn.setText(_('Reset'))

def switch_translator(lang):
    trans = gettext.translation('default', "./locales", languages=[lang])
    trans.install()

def loadLang():
    config = configparser.ConfigParser()
    config.read('settings.cfg')
    cget = config.get

    try:
        return cget('Common', 'lang')
    except:
        return DEFAULT_LANG
   

def main():
    app = QApplication(sys.argv)
    switch_translator(loadLang())
    form = PlottingDataMonitor()
    form.setWindowTitle('SFMonitor')
    form.setWindowIcon( QIcon( 'plot.ico') )
    form.show()
    app.exec_()

if __name__ == "__main__":
    main()
