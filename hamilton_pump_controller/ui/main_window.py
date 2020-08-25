from PyQt5 import QtWidgets, uic
from functools import reduce
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
    STX = "\x02"  # Start of Text
    ETX = "\x03"  # End of Text
    ADDRESS = 1
    ACTIVE_STYLE_STRING = "background-color: mediumspringgreen; \
                           border-radius: 15px; \
                           border: 1px solid #333;"
    CMD_DICT = {'Init': 'ZR',
                'Move': 'A{}',
                'ValveOutput': 'O',
                'ValveInput': 'I',
                'Speed': 'S{}',
                'Acceleration': 'L{}',
                'Delay': 'M{}',
                'Query': 'Q'}

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = uic.loadUi(os.path.dirname(
            os.path.abspath(__file__)) + '/ui_files/mainWindow.ui')
        self.ui.show()

        self.sequence = 1  # Used for Standard Protocol coms

        self.ui.initialize.clicked.connect(self.init_pump)
        self.ui.search.clicked.connect(self.search_for_ports)
        self.ui.ports.currentTextChanged.connect(self.check_port)
        self.ui.set_speed.clicked.connect(self.set_pump_speed)
        self.ui.set_accel.clicked.connect(self.set_pump_accel)

        # Manual Pump control
        self.ui.position_slider.valueChanged.connect(self.change_position)
        self.ui.move_pump.clicked.connect(self.move_to_position)
        self.ui.open_close_valve.clicked.connect(self.open_close_valve)

        # Command Builer Functions
        self.ui.add_move.clicked.connect(self.add_move)
        self.ui.add_delay.clicked.connect(self.add_delay)
        self.ui.add_speed.clicked.connect(self.add_speed)
        self.ui.add_accel.clicked.connect(self.add_accel)
        self.ui.add_valve.clicked.connect(self.add_valve)
        self.ui.move_selected_up.clicked.connect(self.move_up)
        self.ui.move_selected_down.clicked.connect(self.move_down)
        self.ui.remove_command.clicked.connect(self.remove_selected_command)
        self.ui.execute_command.clicked.connect(self.build_and_send_command)
        self.ui.load_file.clicked.connect(self.load_command_file)
        self.ui.save_to_file.clicked.connect(self.save_to_file)

    def _add_checksum(self, command):
        checksum = chr(reduce(lambda x, y: x ^ (ord(y)), command, 0))
        return "".join([command, checksum])

    def _check_response(self, response):
        # This splits the byte string to a list of decimal values
        resp_bytes = list(response)

        # Status byte #5 is 2 position in the byte string 7654321
        status_byte = resp_bytes[2]

        # Check for STX and ETX, Raise Value error if missing
        if resp_bytes[0] != 2 or resp_bytes[-2] != 3:
            raise ValueError("ERROR: Missing Complete Response")

        # Apply bitwise masking
        return {'ready': 0b00100000 & status_byte,
                'error_code': 0x0F & status_byte}

    def _response(self):
        # TODO: Write code for retries if nothing is read back
        response = self.psd4_serial.read(100)
        print(response)
        return response[1:]  # Manually remove leading /0xff

    def _update_next_sequence_num(self):
        # The hamilton pump requires subsequent commands to have an
        # incremental sequence number between 1-7 attached in the string
        if self.sequence >= 7:
            self.sequence = 1
        else:
            self.sequence += 1

    def _wait_if_not_ready(self):
        # Keeps checking pump to see if it's ready
        while not self._check_response(
                self.send_command(self.CMD_DICT['Query']))["ready"]:
            time.sleep(0.1)

    def add_accel(self):
        self.accel_dialog = SelectDialog('/ui_files/add_accel_dialog.ui',
                                         self.get_available_accels())
        self.accel_dialog.show()
        if self.accel_dialog.exec_():
            accel = self.accel_dialog.setting.currentText().split(":")[0]
            self.ui.command_list.addItem('Acceleration:{}'.format(accel))
        self.command_list_changed()

    def add_delay(self):
        self.delay_dialog = Dialog('/ui_files/add_delay_dialog.ui')
        self.delay_dialog.show()
        if self.delay_dialog.exec_():
            delay = self.delay_dialog.delay.text()
            self.ui.command_list.addItem('Delay:{}'.format(delay))
        self.command_list_changed()

    def add_move(self):
        self.move_dialog = Dialog('/ui_files/add_move_dialog.ui')
        self.move_dialog.show()
        if self.move_dialog.exec_():
            pos = self.move_dialog.move_position.text()
            self.ui.command_list.addItem('Move:{}'.format(pos))

    def add_speed(self):
        self.speed_dialog = SelectDialog('/ui_files/add_speed_dialog.ui',
                                         self.get_available_speeds())
        self.speed_dialog.show()
        if self.speed_dialog.exec_():
            speed = self.speed_dialog.setting.currentText().split(":")[0]
            self.ui.command_list.addItem('Speed:{}'.format(speed))
        self.command_list_changed()

    def add_valve(self):
        self.valve_dialog = Dialog('/ui_files/add_valve_dialog.ui')
        self.valve_dialog.show()
        if self.valve_dialog.exec_():
            if self.valve_dialog.output_position.isChecked():
                self.ui.command_list.addItem('ValveOutput:0')
            elif self.valve_dialog.input_position.isChecked():
                self.ui.command_list.addItem('ValveInput:1')
        self.command_list_changed()

    def build_and_send_command(self):
        command = '/1'
        for i in range(self.ui.command_list.count()):
            com, val = self.ui.command_list.item(i).text().split(':')
            command += self.CMD_DICT[com].format(val)
        command += 'R' + self.CR  # add the carriage return
        if (self.psd4_serial.isOpen()):
            self.psd4_serial.write(command.encode())
            time.sleep(1.0)
            print(self.response())

    def change_position(self, value):
        self.ui.position.setText(str(value))

    def check_port(self, value):
        if "/dev/cu.usbserial" in value:
            self.connect_to_port(value)

    def command_list_changed(self):
        if self.ui.command_list.count() > 0:
            self.ui.save_to_file.setEnabled(True)
        else:
            self.ui.save_to_file.setEnabled(False)

    def connect_to_port(self, value):
        self.psd4_serial = serial.Serial(value, 9600, timeout=1)
        self.ui.initialize.setEnabled(True)

    def get_available_accels(self):
        accels = []
        for i, j in enumerate(range(2500, 52500, 2500)):
            accels.append('{}: {} steps per second'.format(i + 1, j))
        return accels

    def get_available_speeds(self):
        file_path = os.getcwd() + '/hamilton_pump_controller/config/speed.json'
        with open(file_path) as f:
            speed = json.load(f)
        speeds = ['{}: {}'.format(k, v) for k, v in speed.items()]
        return speeds

    def init_pump(self):
        self.send_command(self.CMD_DICT['Init'])
        self._wait_if_not_ready()
        print("Pump is Initialized")
        self.ui.initialized.setStyleSheet(self.ACTIVE_STYLE_STRING)
        self.ui.initialized.setText("Pump Online")
        self.populate_speed_and_accel()

    def load_command_file(self):
        file_dialog = QtWidgets.QFileDialog()
        inp = file_dialog.getOpenFileName(filter="Pickle Files (*.p)")[0]
        commands = pickle.load(open(inp, "rb"))
        for command in commands:
            self.ui.command_list.addItem(command)
        self.command_list_changed()

    def move_down(self):
        current_index = self.ui.command_list.currentRow()
        item = self.ui.command_list.takeItem(current_index)
        self.ui.command_list.insertItem(current_index + 1, item)
        self.ui.command_list.setCurrentRow(current_index + 1)

    def move_to_position(self):
        if (self.psd4_serial.isOpen()):
            position = self.ui.position.text().strip()
            command = "/1A{}R".format(position) + self.CR
            self.psd4_serial.write(command.encode())
            print(self.response())

    def move_up(self):
        current_index = self.ui.command_list.currentRow()
        item = self.ui.command_list.takeItem(current_index)
        self.ui.command_list.insertItem(current_index - 1, item)
        self.ui.command_list.setCurrentRow(current_index - 1)

    def open_close_valve(self):
        if self.ui.valve_indicator.text() == "O":
            command = '/1IR' + self.CR
            self.ui.valve_indicator.setText('I')
        else:
            command = '/1OR' + self.CR
            self.ui.valve_indicator.setText('O')
        if (self.psd4_serial.isOpen()):
            self.psd4_serial.write(command.encode())
            print(self.response())

    def populate_speed_and_accel(self):
        self.ui.set_speed.setEnabled(True)
        self.ui.set_accel.setEnabled(True)
        self.ui.speed.setEnabled(True)
        self.ui.accel.setEnabled(True)
        speeds = self.get_available_speeds()
        accels = self.get_available_accels()
        self.ui.speed.addItems(speeds)
        self.ui.accel.addItems(accels)

    def remove_selected_command(self):
        selected = self.ui.command_list.selectedIndexes()
        if len(selected) > 0:
            rows = sorted([index.row() for index in selected], reverse=True)
            for row in rows:
                self.ui.command_list.takeItem(row)
        self.command_list_changed()

    def save_to_file(self):
        commands = []
        for i in range(self.ui.command_list.count()):
            commands.append(self.ui.command_list.item(i).text())
        filename = (os.getcwd() + '/'
                    + datetime.datetime.now().strftime('%Y%M%d-%H%M%S')
                    + '.p')
        pickle.dump(commands, open(filename, "wb"))

    def search_for_ports(self):
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif (sys.platform.startswith('linux')
              or sys.platform.startswith('cygwin')):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/cu.*')
        else:
            raise EnvironmentError('Unsupported platform')
        self.ui.ports.clear()
        self.ui.ports.addItems(ports[::-1])

    def send_command(self, command, retry=5):
        if (self.psd4_serial.isOpen()):
            # Add the other fluff around the basic command
            serial_command = "".join([self.STX, str(self.ADDRESS),
                                      str(self.sequence), command, self.ETX])
            serial_command = self._add_checksum(serial_command)
            while retry > 0:
                self.psd4_serial.reset_input_buffer()
                self.psd4_serial.write(serial_command.encode())
                response = self._response()

                try:
                    print(self._check_response(response))
                    self._update_next_sequence_num()
                    return response
                except ValueError:
                    retry -= 1
            raise Exception('No response from the device, check connections.')
        else:
            raise Exception("No serial port found, check connections.")

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
        self.ui.open_close_valve.setEnabled(True)
        self.ui.move_pump.setEnabled(True)
        self.ui.add_move.setEnabled(True)
        self.ui.add_speed.setEnabled(True)
        self.ui.add_delay.setEnabled(True)
        self.ui.add_valve.setEnabled(True)
        self.ui.add_accel.setEnabled(True)
        self.ui.load_file.setEnabled(True)
        self.ui.move_selected_down.setEnabled(True)
        self.ui.move_selected_up.setEnabled(True)
        self.ui.remove_command.setEnabled(True)
        self.ui.execute_command.setEnabled(True)

    def set_pump_speed(self):
        speed = self.ui.speed.currentText().split(":")[0]
        if (self.psd4_serial.isOpen()):
            command = "/1S{}R".format(speed) + self.CR
            self.psd4_serial.write(command.encode())
            self.ui.speed_set.setStyleSheet(self.ACTIVE_STYLE_STRING)
            self.ui.speed_set.setText("Speed Set: {}".format(speed))
            print(self.response())
