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
NFLOWS = 3
NTRACE = 14
WTRACE = 3
NCURVES = 3

DEFAULT_PLOT_PAGE = 20
DEFAULT_BAUD_RATE = 6
DEFAULT_DATA_FORMAT = 0
DEFAULT_UPDATE_FREQ = 50
DEFAULT_MIN_SCALE = 0
DEFAULT_MAX_SCALE = 256
DEFAULT_MAJOR_SCALE = 32
DEFAULT_PLOT_MODE = 'Plot'
DEFAULT_LANG = 'en'

DEFAULT_FLOW_VALUE_SIZE = 1
DEFAULT_FLOW_VALUE_SEPARATOR = True
DEFAULT_FLOW_TRACE = False
DEFAULT_FLOW_UNSIGNED = True
DEFAULT_FLOW_SCATTER = True
DEFAULT_FLOW_COLOR = '#0080FF'
DEFAULT_FLOW_ENABLED = False

MD_PLOT = 0
MD_VECTOR = 1
MD_POSITION = 2

_data_formats = ('Simple','Complex v(t)','Complex y(x)')
_plot_modes = ('Plot','Vector','Position')
_baud_rates = ('110', '300', '600', '1200', '2400', '4800',
               '9600', '14400', '19200', '38400', '57600',
               '115200', '230400', '460800', '921600')
_flow_colors = ((0,255,0),(255,255,0),(0,0,255))
_langs = {'English':'en','Russian':'ru'}
_langsi = {'en':'English','ru':'Russian'}

_last_point = 0

loc = None

class PlottingDataMonitor(QMainWindow):

    data_format = DEFAULT_DATA_FORMAT
    port_name = 0
    port_name_opened = None
    baud_rate = 0
    plot_page = DEFAULT_PLOT_PAGE
    plot_scale_x = {}
    plot_scale_y = {}
    flow_props = [{} for i in range(NFLOWS)]
    data = [[] for i in range(NFLOWS)]
    flow_value_size = 2
    flow_separator = True
    flow_trace = False
    curves = NCURVES*[None]
    positions = []
    old_positions = []
    lang = 'en'
    status = ''
    
    def __init__(self, parent=None):
        super(PlottingDataMonitor, self).__init__(parent)
        
        self.monitor_active = False
        self.com_monitor = None
        self.com_data_q = None
        self.com_error_q = None

        # curve enabled
        self.flows_e = NCURVES*[False]

        # three data flows
        create_curve  = [[] for i in range(NCURVES)]

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
        
        # Packet format
        try:
            self.data_format = int(cget('Data', 'format'))
        except:
            self.data_format = DEFAULT_DATA_FORMAT

        # Flow props
        self.flow_value_size = int(cget('Flow', 'value_size', fallback=DEFAULT_FLOW_VALUE_SIZE))
        self.flow_separator = cget('Flow', 'separator', fallback=DEFAULT_FLOW_VALUE_SEPARATOR)=='True' and True or False
        self.flow_trace = cget('Flow', 'trace', fallback=DEFAULT_FLOW_TRACE)=='True' and True or False

        for idx in range(NFLOWS):
            self.flow_props[idx]['unsigned'] = cget('Flow', 'unsigned_%d' % idx, fallback=DEFAULT_FLOW_UNSIGNED)=='True' and True or False
            self.flow_props[idx]['color'] = strToColor(cget('Flow', 'color_%d' % idx, fallback=DEFAULT_FLOW_COLOR))
            self.flow_props[idx]['scatter'] = cget('Flow', 'scatter_%d' % idx, fallback=DEFAULT_FLOW_SCATTER)=='True' and True or False
            self.flows_e[idx] = cget('Flow', 'visible_%d' % idx, fallback=DEFAULT_FLOW_ENABLED)=='True' and True or False
        
        # Plot props
        self.plot_scale_x['min'] = int(cget('Plot', 'min_scale_x', fallback=DEFAULT_MIN_SCALE))
        self.plot_scale_x['max'] = int(cget('Plot', 'max_scale_x', fallback=DEFAULT_MAX_SCALE))
        self.plot_scale_x['major'] = int(cget('Plot', 'major_scale_x', fallback=DEFAULT_MAJOR_SCALE))
        
        self.plot_scale_y['min'] = int(cget('Plot', 'min_scale_y', fallback=DEFAULT_MIN_SCALE))
        self.plot_scale_y['max'] = int(cget('Plot', 'max_scale_y', fallback=DEFAULT_MAX_SCALE))
        self.plot_scale_y['major'] = int(cget('Plot', 'major_scale_y', fallback=DEFAULT_MAJOR_SCALE))
        
        self.plot_page = int(cget('Plot', 'page', fallback=DEFAULT_PLOT_PAGE))
        self.plot_mode = _plot_modes.index(cget('Plot', 'mode', fallback=DEFAULT_PLOT_MODE))

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
        
        # Packet format
        csec('Data')
        cset('Data', 'format', str(self.data_format))

        # Flow props
        csec('Flow')
        cset('Flow', 'value_size', str(self.flow_value_size))
        cset('Flow', 'separator', str(self.flow_separator))
        cset('Flow', 'trace', str(self.flow_trace))
        for idx in range(NFLOWS):
            cset('Flow', 'unsigned_%d' % idx, str(self.flow_props[idx]['unsigned']))
            cset('Flow', 'color_%d' % idx, colorToStr(self.flow_props[idx]['color']))
            cset('Flow', 'scatter_%d' % idx, str(self.flow_props[idx]['scatter']))
            cset('Flow', 'visible_%d' % idx, str(self.flows_e[idx]))
            
        # Plot scale
        csec('Plot')
        cset('Plot', 'min_scale_x', str(self.plot_scale_x['min']))
        cset('Plot', 'max_scale_x', str(self.plot_scale_x['max']))
        cset('Plot', 'major_scale_x', str(self.plot_scale_x['major']))

        cset('Plot', 'min_scale_y', str(self.plot_scale_y['min']))
        cset('Plot', 'max_scale_y', str(self.plot_scale_y['max']))
        cset('Plot', 'major_scale_y', str(self.plot_scale_y['major']))

        cset('Plot', 'page', str(self.plot_page))
        cset('Plot', 'mode', _plot_modes[self.plot_mode])

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

    def create_slider(self, ticks=10):
        sld = QSlider(Qt.Horizontal, self)
        sld.setFocusPolicy(Qt.NoFocus)
        sld.setTickInterval(ticks)
        sld.setTickPosition(QSlider.TicksBelow)        
        return sld

    def create_status_bar(self):
        self.status = 'Monitor idle'
        self.status_text = QLabel(_(self.status))
        self.statusBar().addWidget(self.status_text, 1)
    
    # Positions
    def create_positions(self):
        self.create_position(trace=0)
        self.old_positions.append([0,0])
        for i in range(1,NTRACE+1):
            self.create_position(i)
            self.old_positions.append([0,0])

    def create_position(self, trace=0):
        sz = self.plot_scale_x['major']
        self.positions.append( QGraphicsRectItem( 0, 0, sz, sz ))
        self.positions[-1].setPen( pg.mkPen( (self.flow_props[0]['color'] + (255-trace*16,)), width=WTRACE ))
        self.plot.addItem(self.positions[-1])

    def reset_positions(self):
        if not len(self.positions):
            return
        sz = self.plot_scale_x['major']
        for i in range(NTRACE+1):
            self.positions[i].setRect(0, 0, sz, sz)
        self.old_positions = (NTRACE+1)*[[0,0]]

    def remove_positions(self):
        if not len(self.positions):
            return
        for i in range(NTRACE+1):
            self.plot.removeItem(self.positions[i])
        self.positions = []
        self.old_positions = []

    def show_positions(self, force_trace = False):
        if self.plot_mode == MD_POSITION:
            self.positions[0].show()
            if self.flow_trace:
                for i in range(1,NTRACE+1):
                    self.positions[i].show()
            elif force_trace:
                for i in range(1,NTRACE+1):
                    self.positions[i].hide()
                
        else:
            for i in range(NTRACE+1):
                self.positions[i].hide()            

    def color_positions(self):
        self.positions[0].setPen( pg.mkPen(*self.flow_props[0]['color']) )
        if self.flow_trace:
            for i in range(1,NTRACE+1):
                self.positions[i].setPen( pg.mkPen(*(self.flow_props[0]['color'] + (255-i*16,)), width=WTRACE) )

    # Plot
    def create_plot(self):
        plot = pg.PlotWidget()

        if self.plot_mode == MD_PLOT:
            plot.setLabel('left', _('Value'), '')
            plot.setLabel('bottom', _('Time'), _('Sec'))
            
        elif self.plot_mode in (MD_VECTOR, MD_POSITION):
            plot.setLabel('left', 'Y', '')
            plot.setLabel('bottom', 'X', '')

        plot.showGrid(1,1)
        
        return plot
    
    def create_curve(self, plot, idx, scatter, color):
        if scatter:
            self.curves[idx] = pg.ScatterPlotItem(size=2, pen=pg.mkPen(*color), brush=pg.mkBrush(None))
            spots = [{'pos': [0,0], 'data': 1}]
            self.curves[idx].addPoints(spots)
            plot.addItem(self.curves[idx])
        else:
            self.curves[idx] = plot.plot([], pen=color)

    def remove_curves(self):
        for i,e in enumerate(self.flows_e):
            if e:
                self.flows_cb[i].toggle();
                self.plot.removeItem(self.curves[i])
        self.curves = NCURVES*[None]

    def reset_curves(self):
        for i,e in enumerate(self.flows_e):
            if e:
                self.curves[i].setData([],[])
        self.data = [[] for i in range(NCURVES)]

    def rescale_plot(self):
        self.plot.setYRange(self.plot_scale_y['min'], self.plot_scale_y['max'], padding=0)

        if self.plot_mode == MD_PLOT:
            self.plot.setXRange(0, self.plot_page, padding=0)
        elif self.plot_mode in (MD_VECTOR, MD_POSITION):
            self.plot.setXRange(self.plot_scale_x['min'], self.plot_scale_x['max'], padding=0)

    def create_items( self ):
        for i,e in enumerate(self.flows_e):
            if e:
                if self.plot_mode in (MD_PLOT, MD_VECTOR):
                    self.create_curve(self.plot, i, self.flow_props[i]['scatter'], self.flow_props[i]['color'])
                elif i == 0 and self.plot_mode == MD_POSITION:
                    self.create_positions()

    def remove_items( self, force=False ):
        for i,e in enumerate(self.flows_e):
            if not e or force:
                if self.plot_mode in (MD_PLOT, MD_VECTOR):
                    if self.curves[i] is not None:
                        self.plot.removeItem(self.curves[i])
                    self.curves[i] = None
                elif i == 0 and self.plot_mode == MD_POSITION:
                    self.remove_positions()

    def reset_items( self ):
        if self.plot_mode in (MD_PLOT, MD_VECTOR):
            self.reset_curves()
        elif self.plot_mode == MD_POSITION:
            self.reset_positions()
    
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

        # Data flow control
        #
        data_layout = QHBoxLayout()

        # data format
        v_layout = QVBoxLayout()
        format_layout = QHBoxLayout()
        self.data_format_l = QLabel(_('Data format:'))
        self.data_format_cb = QComboBox()
        self.data_format_cb.addItems([_(df) for df in _data_formats])
        self.data_format_cb.setCurrentIndex(self.data_format)

        self.data_format_cb.currentIndexChanged.connect(self.on_change_data_format)

        format_layout.addWidget(self.data_format_l)
        format_layout.addWidget(self.data_format_cb, 0)
        v_layout.addLayout(format_layout)

        mode_layout = QHBoxLayout()
        self.plot_mode_l = QLabel(_('Plot mode:'))
        self.plot_mode_cb = QComboBox()
        self.plot_mode_cb.addItems([_(pm) for pm in _plot_modes])
        self.plot_mode_cb.setCurrentIndex(self.plot_mode)
        if self.data_format in (FMT_SIMPLE, FMT_COMPLEX_VT):
            self.plot_mode_cb.setEnabled(False)

        self.plot_mode_cb.currentIndexChanged.connect(self.on_change_plot_mode)
        
        mode_layout.addWidget(self.plot_mode_l)
        mode_layout.addWidget(self.plot_mode_cb, 0)
        v_layout.addLayout(mode_layout)

        self.data_groupbox = QGroupBox(_('Data'))
        self.data_groupbox.setLayout(v_layout)
        data_layout.addWidget(self.data_groupbox)
        
        
        # frequency slider
        freq_layout = QVBoxLayout()
        self.update_freq = self.create_slider(10)
        self.update_freq.setGeometry(30, 40, 100, 30)
        self.update_freq.valueChanged[int].connect(self.on_freq_change)

        self.update_freq_l = QLabel(_('Update frequency = %s (Hz)') % self.update_freq.value())
        self.update_freq_l.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.update_freq.setValue(DEFAULT_UPDATE_FREQ)

        freq_layout.addWidget(self.update_freq)
        freq_layout.addWidget(self.update_freq_l)

        self.freq_groupbox = QGroupBox(_('Update frequency'))
        self.freq_groupbox.setLayout(freq_layout)
        data_layout.addWidget(self.freq_groupbox)
        
        # Plot
        #
        self.plot = self.create_plot()
        self.rescale_plot();
        
        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.plot)
        
        self.plot_groupbox = QGroupBox(_('Plot'))
        self.plot_groupbox.setLayout(plot_layout)

        # Position mark
        #
        #self.create_positions()
        #self.show_positions()

        # plot select
        select_layout = QVBoxLayout()
        self.flows_cb = []
        for i,e in enumerate(self.flows_e):
            cb = self.create_checkbox(_('Flow #%d') % i)
            cb.toggle()
            cb.stateChanged.connect(self.on_select_curve)
            self.flows_cb.append(cb)
            select_layout.addWidget(self.flows_cb[-1])
            if e: self.flows_cb[i].toggle()
                
        self.flow_groupbox = QGroupBox(_('Data flows'))
        self.flow_groupbox.setLayout(select_layout)
        data_layout.addWidget(self.flow_groupbox)
        
        # Main frame and layout
        #
        self.main_frame = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.port_groupbox)
        main_layout.addLayout(data_layout)
        main_layout.addWidget(self.plot_groupbox)
        main_layout.addStretch(1)
        self.main_frame.setLayout(main_layout)
        
        self.setCentralWidget(self.main_frame)
        self.set_actions_enable_state()
        #self.create_items()

    def create_menu(self):
        # file menu
        self.file_menu = self.menuBar().addMenu(_("File"))
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

        # data menu
        self.data_menu = self.menuBar().addMenu(_("Data"))

        self.set_scale_action = self.create_action(_("Set plot scale"), slot=self.on_set_scale)
        self.setup_flows_action = self.create_action(_("Setup flows"), slot=self.on_setup_flows)

        self.add_actions(self.data_menu, (self.set_scale_action, self.setup_flows_action))

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

    def on_change_data_format( self, idx ):
        self.data_format = idx
        if idx in ( FMT_SIMPLE, FMT_COMPLEX_VT ):
            self.plot_mode_cb.setCurrentIndex(0)
            self.plot_mode_cb.setEnabled(False)
        elif idx == FMT_COMPLEX_YX:
            self.plot_mode_cb.setEnabled(True)
        self.reset()

    def on_change_plot_mode( self, idx ):
        self.remove_items(force=True)
        self.plot_mode = idx
        if self.plot_mode in (MD_PLOT, MD_VECTOR):
            for i,e in enumerate(self.flows_e[1:]):
                self.flows_cb[i+1].setEnabled(True)
        elif self.plot_mode == MD_POSITION:
            for i,e in enumerate(self.flows_e[1:]):
                if e: self.flows_cb[i].toggle()
                self.flows_e[i+1] = False
                self.flows_cb[i+1].setEnabled(False)
            
        self.create_items()
        self.reset_items()

    def on_select_curve(self, state):
        for i,cb in enumerate(self.flows_cb):
            self.flows_e[i] = cb.isChecked()

        self.remove_items()
        self.create_items()
            
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

    def on_set_scale(self):
        groups = []
        
        groups.append(((_('Plot page size'), self.plot_page),))

        groups.append(((_('Min value'), self.plot_scale_x['min']),
                       (_('Max value'), self.plot_scale_x['max']),
                       (_('Major tick'), self.plot_scale_x['major']),))

        groups.append(((_('Min value'), self.plot_scale_y['min']),
                       (_('Max value'), self.plot_scale_y['max']),
                       (_('Major tick'), self.plot_scale_y['major']),))

        groups = ((groups[0], _("Common"), _("Setup common plot properties")),
                  (groups[1], _("Axis X"), _("Set axis X scale")),
                  (groups[2], _("Axis Y"), _("Set axis Y scale")),)

        results = fedit(groups, title="Plot scale")

        if results:
            self.plot_page = int(results[0][0])

            self.plot_scale_x['min'] = int(results[1][0])
            self.plot_scale_x['max'] = int(results[1][1])
            self.plot_scale_x['major'] = int(results[1][2])

            self.plot_scale_y['min'] = int(results[2][0])
            self.plot_scale_y['max'] = int(results[2][1])
            self.plot_scale_y['major'] = int(results[2][2])

            self.rescale_plot()

    def on_setup_flows(self):
        groups = []
        groups.append( (( _('Value size in packet'), self.flow_value_size ),
                        ( _('Value separator'), self.flow_separator ),
                        ( _('Draw trace'), self.flow_trace )
                       ))

        for idx in range(NFLOWS):
            groups.append(( ( _('Unsigned'), self.flow_props[idx].get('unsigned', True)),
                            ( _('Color'), colorToStr(self.flow_props[idx].get('color', _flow_colors[idx]) )),
                            ( _('Scatter'), self.flow_props[idx].get('scatter', False))
                          ))
        groups = ((groups[0], _("Common"), _("Setup common flow properties")),
                  (groups[1], _("Flow #%d") % 1, _("Set flow #%d properties") % 1),
                  (groups[2], _("Flow #%d") % 2, _("Set flow #%d properties") % 2),
                  (groups[3], _("Flow #%d") % 3, _("Set flow #%d properties") % 3))
        
        results = fedit(groups, title=_("Data flow properties")+' '*32)

        if results:
            self.flow_value_size = int(results[0][0])
            self.flow_separator = bool(results[0][1])
            self.flow_trace = bool(results[0][2])

            for idx in range(NFLOWS):
                self.flow_props[idx]['unsigned'] = results[idx+1][0]
                self.flow_props[idx]['color'] = strToColor(results[idx+1][1])
                self.flow_props[idx]['scatter'] = results[idx+1][2]

                if self.curves[idx]:
                    self.curves[idx].setPen( pg.mkPen(*self.flow_props[idx]['color']) )

            if self.plot_mode == MD_POSITION:
                self.show_positions(force_trace=True)
                self.color_positions()
             
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
            data_format=self.data_format,
            value_size=self.flow_value_size,
            separator=self.flow_separator)

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

        update_freq = self.update_freq.value()+1
        if update_freq > 0:
            self.timer.start(1000 / update_freq)

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
        #self.rescale_plot()

    def on_reset(self):
        global _last_point
        _last_point = 0
        #self.plot.setXRange(0, self.plot_page, padding=0)

        self.reset_items()
        self.rescale_plot()
        
    def on_freq_change(self):
        """ When the freq slider is moved, it sets the update interval
            of the timer.
        """
        update_freq = self.update_freq.value()+1
        self.update_freq_l.setText(_('Update frequency = %s (Hz)') % update_freq)

        if self.timer.isActive():
            self.timer.setInterval(1000.0 / update_freq)

    def update_monitor(self):
        """ Updates the state of the monitor window with new 
            data. The livefeed is used to find out whether new
            data was received since the last update. If not, 
            nothing is updated.
        """
        global _last_point
        size = len(self.data[0])
        pm = self.plot_mode

        # emergency exit
        if not self.data[0]:
            return

        # page switching
        if pm == MD_PLOT and self.data[0][-1][0] >= _last_point+self.plot_page:
            _last_point = self.data[0][-1][0]
            self.plot.setXRange(_last_point, _last_point+self.plot_page, padding=0)
            self.data = [[] for i in range(NCURVES)]

        for i,enabled in enumerate(self.flows_e):
            if enabled and self.data[i]:
                if pm in (MD_PLOT, MD_VECTOR):
                    xdata = [s[0] for s in self.data[i]]
                    ydata = [s[1] for s in self.data[i]]
                    self.curves[i].setData(xdata, ydata)
                elif pm == MD_POSITION:
                    xdata = self.data[i][-1][0]
                    ydata = self.data[i][-1][1]
                    if self.flow_trace:
                        for i in reversed(range(1,NTRACE+1)):
                            self.positions[i].setRect(self.old_positions[i][0], self.old_positions[i][1], self.plot_scale_x['major'], self.plot_scale_x['major'])
                            self.old_positions[i] = self.old_positions[i-1]
                        self.old_positions[0] = [xdata, ydata]
                    self.positions[0].setRect(xdata, ydata, self.plot_scale_x['major'], self.plot_scale_x['major'])
        
    def read_serial_data(self):
        """ Called periodically by the update timer to read data
            from the serial port.
        """
        qdata = list(get_all_from_queue(self.data_q))
        df = self.data_format
        pm = self.plot_mode
        
        # Simple        
        if df == FMT_SIMPLE:
            for d in qdata:
                self.data[0].append( ( d[0], typecast(d[1], self.flow_props[0]['unsigned']) ))

        else:
            # Complex 1
            if df == FMT_COMPLEX_VT:
                for d in qdata:
                    #print (d)
                    # cycle flows
                    for i,flow in enumerate(d[1]):
                        value = join_bytes(flow, self.flow_props[i]['unsigned'], self.flow_value_size)
                        self.data[i].append( ( d[0], value ))

            # Complex 2
            elif df == FMT_COMPLEX_YX:
                for d in qdata:
                    if pm == MD_VECTOR:
                        self.data[0] = []
                        for i,v in enumerate(d[1]):
                            x = i
                            y = join_bytes(v, self.flow_props[0]['unsigned'], self.flow_value_size)
                            self.data[0].append( ( x, y ))
                    elif pm == MD_POSITION:
                        for i in range(int(len(d[1])/2)):
                            x = join_bytes(d[1][i], self.flow_props[0]['unsigned'], self.flow_value_size)
                            y = join_bytes(d[1][i+1], self.flow_props[0]['unsigned'], self.flow_value_size)
                            self.data[i].append( ( x, y ))

                    elif pm == MD_PLOT:    
                        _timestamp = join_bytes( d[1][0], 1, self.flow_value_size )
                        for i,flow in enumerate(d[1][1:]):
                            value = join_bytes(flow, self.flow_props[i]['unsigned'], self.flow_value_size)
                            self.data[i].append( ( _timestamp, value ))

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
        self.plot_mode_l.setText(_('Plot mode:'))
        self.data_format_l.setText(_('Data format:'))
        self.data_groupbox.setTitle(_('Data'))
        self.port_groupbox.setTitle(_('COM port'))
        self.flow_groupbox.setTitle(_('Data flows'))
        self.plot_groupbox.setTitle(_('Plot'))

        for i in range(len(self.flows_e)):
            self.flows_cb[i].setText(_('Flow #%d') % i)

        #combobox
        for i,df in enumerate(_data_formats):
            self.data_format_cb.setItemText(i, _(df))
        for i,pm in enumerate(_plot_modes):
            self.plot_mode_cb.setItemText(i, _(pm))
        
        #plot
        if self.plot_mode == MD_PLOT:
            self.plot.setLabel('left', _('Value'), '')
            self.plot.setLabel('bottom', _('Time'), _('Sec'))
        elif self.plot_mode in (MD_VECTOR, MD_POSITION):
            self.plot.setLabel('left', 'Y', '')
            self.plot.setLabel('bottom', 'X', '')
        
        #menu
        self.help_menu.setTitle(_('Help'))
        self.about_action.setText(_('About'))
        self.file_menu.setTitle(_('File'))
        self.selectport_action.setText(_('Select COM port'))
        self.start_action.setText(_('Start monitor'))
        self.stop_action.setText(_('Stop monitor'))
        self.prefs_action.setText(_('Preferences'))
        self.exit_action.setText(_('Exit'))
        self.data_menu.setTitle(_('Data'))
        self.set_scale_action.setText(_('Set plot scale'))
        self.setup_flows_action.setText(_('Setup flows'))

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
