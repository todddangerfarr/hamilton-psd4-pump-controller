from PyQt5 import QtWidgets, uic
import datetime
import pickle
import serial
import time
import json
import glob
import sys
import os

from .dialog import Dialog
from .select_dialog import SelectDialog


class MainWindow(QtWidgets.QMainWindow):

    CR = chr(13)  # carriage return
    IMAGE_SIZE = (285, 165)
    ACTIVE_STYLE_STRING = "background-color: mediumspringgreen; \
                           border-radius: 15px; \
                           border: 1px solid #333;"
    CMD_DICT = {'Move': 'A{}',
                'ValveOutput': 'O',
                'ValveInput': 'I',
                'Speed': 'S{}',
                'Acceleration': 'L{}',
                'Delay': 'M{}'}

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

        # Command Builer Functions
        self.ui.add_move.clicked.connect(self.add_move)
        self.ui.add_delay.clicked.connect(self.add_delay)
        self.ui.add_speed.clicked.connect(self.add_speed)
        self.ui.add_accel.clicked.connect(self.add_accel)
        self.ui.add_valve.clicked.connect(self.add_valve)
        self.ui.move_selected_up.clicked.connect(self.move_up)
        self.ui.move_selected_down.clicked.connect(self.move_down)
        self.ui.remove_command.clicked.connect(self.remove_selected_command)
        self.ui.execute_command.clicked.connect(self.execute_commands)
        self.ui.load_file.clicked.connect(self.load_command_file)
        self.ui.save_to_file.clicked.connect(self.save_to_file)

    def add_move(self):
        self.move_dialog = Dialog('/ui_files/add_move_dialog.ui')
        self.move_dialog.show()
        if self.move_dialog.exec_():
            pos = self.move_dialog.move_position.text()
            self.ui.command_list.addItem('Move:{}'.format(pos))

    def add_delay(self):
        self.delay_dialog = Dialog('/ui_files/add_delay_dialog.ui')
        self.delay_dialog.show()
        if self.delay_dialog.exec_():
            delay = self.delay_dialog.delay.text()
            self.ui.command_list.addItem('Delay:{}'.format(delay))

    def add_valve(self):
        self.valve_dialog = Dialog('/ui_files/add_valve_dialog.ui')
        self.valve_dialog.show()
        if self.valve_dialog.exec_():
            if self.valve_dialog.output_position.isChecked():
                self.ui.command_list.addItem('ValveOutput:0')
            elif self.valve_dialog.input_position.isChecked():
                self.ui.command_list.addItem('ValveInput:1')

    def add_speed(self):
        self.speed_dialog = SelectDialog('/ui_files/add_speed_dialog.ui',
                                         self.get_available_speeds())
        self.speed_dialog.show()
        if self.speed_dialog.exec_():
            speed = self.speed_dialog.setting.currentText().split(":")[0]
            self.ui.command_list.addItem('Speed:{}'.format(speed))

    def add_accel(self):
        self.accel_dialog = SelectDialog('/ui_files/add_accel_dialog.ui',
                                         self.get_available_accels())
        self.accel_dialog.show()
        if self.accel_dialog.exec_():
            accel = self.accel_dialog.setting.currentText().split(":")[0]
            self.ui.command_list.addItem('Acceleration:{}'.format(accel))

    def move_up(self):
        current_index = self.ui.command_list.currentRow()
        item = self.ui.command_list.takeItem(current_index)
        self.ui.command_list.insertItem(current_index - 1, item)
        self.ui.command_list.setCurrentRow(current_index - 1)

    def move_down(self):
        current_index = self.ui.command_list.currentRow()
        item = self.ui.command_list.takeItem(current_index)
        self.ui.command_list.insertItem(current_index + 1, item)
        self.ui.command_list.setCurrentRow(current_index + 1)

    def remove_selected_command(self):
        selected = self.ui.command_list.selectedIndexes()
        if len(selected) > 0:
            rows = sorted([index.row() for index in selected], reverse=True)
            for row in rows:
                self.ui.command_list.takeItem(row)

    def execute_commands(self):
        command = '/1'
        for i in range(self.ui.command_list.count()):
            com, val = self.ui.command_list.item(i).text().split(':')
            command += self.CMD_DICT[com].format(val)
        command += 'R' + self.CR  # add the carriage return
        if (self.psd4_serial.isOpen()):
            self.psd4_serial.write(command.encode())
            time.sleep(1.0)
            print(self.response())

    def check_port(self, value):
        if "/dev/cu.usbserial" in value:
            self.connect_to_port(value)

    def load_command_file(self):
        file_dialog = QtWidgets.QFileDialog()
        inp = file_dialog.getOpenFileName(filter="Pickle Files (*.p)")[0]
        commands = pickle.load(open(inp, "rb"))
        for command in commands:
            self.ui.command_list.addItem(command)

    def save_to_file(self):
        commands = []
        for i in range(self.ui.command_list.count()):
            commands.append(self.ui.command_list.item(i).text())
        filename = (os.getcwd() + '/'
                    + datetime.datetime.now().strftime('%Y%M%d-%H%M%S')
                    + '.p')
        pickle.dump(commands, open(filename, "wb"))

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
        self.ui.ports.addItems(ports[::-1])

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

    def get_available_speeds(self):
        file_path = os.getcwd() + '/hamilton_pump_controller/config/speed.json'
        with open(file_path) as f:
            speed = json.load(f)
        speeds = ['{}: {}'.format(k, v) for k, v in speed.items()]
        return speeds

    def get_available_accels(self):
        accels = []
        for i, j in enumerate(range(2500, 52500, 2500)):
            accels.append('{}: {} steps per second'.format(i + 1, j))
        return accels

    def populate_speed_and_accel(self):
        self.ui.set_speed.setEnabled(True)
        self.ui.set_accel.setEnabled(True)
        self.ui.speed.setEnabled(True)
        self.ui.accel.setEnabled(True)
        speeds = self.get_available_speeds()
        accels = self.get_available_accels()
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
