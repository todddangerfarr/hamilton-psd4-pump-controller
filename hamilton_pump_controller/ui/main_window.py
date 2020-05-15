from PyQt5 import QtWidgets, uic
import serial
import time
import json
import glob
import sys
import os

from .move_dialog import MoveDialog
from .valve_dialog import ValveDialog


class MainWindow(QtWidgets.QMainWindow):

    CR = chr(13)  # carriage return
    IMAGE_SIZE = (285, 165)
    ACTIVE_STYLE_STRING = "background-color: mediumspringgreen; \
                           border-radius: 15px; \
                           border: 1px solid #333;"
    COM_DICT = {'Move': 'A{}',
                'ValveOutput': 'O',
                'ValveInput': 'I'}

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi(os.path.dirname(
            os.path.abspath(__file__)) + '/ui_files/mainWindow.ui')
        self.ui.show()

        self.ui.initialize.clicked.connect(self.init_pump)
        self.ui.search.clicked.connect(self.search_for_ports)
        self.ui.ports.currentTextChanged.connect(self.check_port)
        self.ui.move_pump.clicked.connect(self.move_to_position)
        self.ui.set_speed.clicked.connect(self.set_pump_speed)
        self.ui.set_accel.clicked.connect(self.set_pump_accel)
        self.ui.position_slider.valueChanged.connect(self.change_position)
        self.ui.add_move.clicked.connect(self.add_move)
        self.ui.add_delay.clicked.connect(self.add_delay)
        self.ui.add_speed.clicked.connect(self.add_speed)
        self.ui.add_accel.clicked.connect(self.add_accel)
        self.ui.add_valve.clicked.connect(self.add_valve)
        self.ui.execute_command.clicked.connect(self.execute_commands)

    def add_move(self):
        self.dialog = MoveDialog()
        self.dialog.show()
        if self.dialog.exec_():
            pos = self.dialog.move_position.text()
            self.ui.command_list_widget.addItem('Move:{}'.format(pos))

    def add_delay(self):
        self.ui.command_list_widget.addItem('Delay')

    def add_valve(self):
        self.dialog = ValveDialog()
        self.dialog.show()
        if self.dialog.exec_():
            pos = self.dialog.move_position.text()
            if pos == '0':
                self.ui.command_list_widget.addItem('ValveOutput:0')
            else:
                self.ui.command_list_widget.addItem('ValveInput:1')

    def add_speed(self):
        self.ui.command_list_widget.addItem('Speed')

    def add_accel(self):
        self.ui.command_list_widget.addItem('Accel')

    def execute_commands(self):
        command = '/1'
        for i in range(self.ui.command_list_widget.count()):
            com, val = self.ui.command_list_widget.item(i).text().split(':')
            command = self.COM_DICT[com].format(val) + self.CR
            print(command)
            if (self.psd4_serial.isOpen()):
                self.psd4_serial.write(command.encode())
                time.sleep(1.5)


    def check_port(self, value):
        if "/dev/cu.usbserial" in value:
            self.connect_to_port(value)

    def change_position(self, value):
        self.ui.position.setText(str(value))

    def search_for_ports(self):
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/cu.*')
        else:
            raise EnvironmentError('Unsupported platform')
        self.ui.ports.clear()
        self.ui.ports.addItems(ports)

    def connect_to_port(self, value):
        self.psd4_serial = serial.Serial(value, 9600, timeout=1)
        self.ui.initialize.setEnabled(True)

    def init_pump(self):
        if (self.psd4_serial.isOpen()):
            command = "/1ZR" + self.CR
            self.psd4_serial.write(command.encode())
            while True:
                resp = self.response()
                if resp != b'':
                    time.sleep(.25)
                else:
                    break
            time.sleep(2)  # need to find better solution here.
            print("Pump is Initialized")
            self.ui.initialized.setStyleSheet(self.ACTIVE_STYLE_STRING)
            self.ui.initialized.setText("Pump Online")
            self.populate_speed_and_accel()

    def populate_speed_and_accel(self):
        self.ui.set_speed.setEnabled(True)
        self.ui.set_accel.setEnabled(True)
        self.ui.speed.setEnabled(True)
        self.ui.accel.setEnabled(True)
        with open(os.getcwd() + '/hamilton_pump_controller/config/speed.json') as f:
            speed = json.load(f)
        speeds = ['{}: {}'.format(k, v) for k, v in speed.items()]
        accels = []
        for i, j in enumerate(range(2500, 52500, 2500)):
            accels.append('{}: {} steps per second'.format(i + 1, j))
        self.ui.speed.addItems(speeds)
        self.ui.accel.addItems(accels)

    def response(self):
        response = self.psd4_serial.read(2)
        return response

    def set_pump_accel(self):
        accel = self.ui.accel.currentText().split(":")[0]
        if (self.psd4_serial.isOpen()):
            command = "/1L{}R".format(accel) + self.CR
            self.psd4_serial.write(command.encode())
            self.ui.accel_set.setStyleSheet(self.ACTIVE_STYLE_STRING)
            self.ui.accel_set.setText("Accel Set: {}".format(accel))
            print(self.response())
        self.ui.position.setEnabled(True)
        self.ui.position_slider.setEnabled(True)
        self.ui.move_pump.setEnabled(True)
        self.ui.add_move.setEnabled(True)
        self.ui.add_speed.setEnabled(True)
        self.ui.add_delay.setEnabled(True)
        self.ui.add_valve.setEnabled(True)
        self.ui.add_accel.setEnabled(True)
        self.ui.execute_command.setEnabled(True)

    def set_pump_speed(self):
        speed = self.ui.speed.currentText().split(":")[0]
        if (self.psd4_serial.isOpen()):
            command = "/1S{}R".format(speed) + self.CR
            self.psd4_serial.write(command.encode())
            self.ui.speed_set.setStyleSheet(self.ACTIVE_STYLE_STRING)
            self.ui.speed_set.setText("Speed Set: {}".format(speed))
            print(self.response())

    def move_to_position(self):
        if (self.psd4_serial.isOpen()):
            position = self.ui.position.text().strip()
            command = "/1A{}R".format(position) + self.CR
            self.psd4_serial.write(command.encode())
            print(self.response())
