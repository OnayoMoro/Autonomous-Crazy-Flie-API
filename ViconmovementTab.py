#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2013 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
#  02110-1301, USA.

"""
An example template for a tab in the Crazyflie Client. It comes pre-configured
with the necessary QT Signals to wrap Crazyflie API callbacks and also
connects the connected/disconnected callbacks.
"""

import logging
import time

from PyQt5 import uic
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMessageBox

import cfclient
from cfclient.ui.tab import Tab

try:
    import zmq
except ImportError as e:
    raise Exception("ZMQ library probably not installed ({})".format(e))

__author__ = 'Bitcraze AB and Onayo Moro'
__all__ = ['ViconMovementTab']

logger = logging.getLogger(__name__)

viconmovement_tab_class = uic.loadUiType(cfclient.module_path +
                                   "/ui/tabs/viconMovementTab.ui")[0]

class ViconMovementTab(Tab, viconmovement_tab_class):
    """Tab for plotting logging data"""

    _connected_signal = pyqtSignal(str)
    _disconnected_signal = pyqtSignal(str)
    _log_data_signal = pyqtSignal(int, object, object)
    _log_error_signal = pyqtSignal(object, str)
    _param_updated_signal = pyqtSignal(str, str)

    def __init__(self, tabWidget, helper, *args):
        super(ViconMovementTab, self).__init__(*args)
        self.setupUi(self)

        self.tabName = "Vicon Movement"
        self.menuName = "Vicon Movement"
        self.tabWidget = tabWidget

        self._helper = helper

        # Always wrap callbacks from Crazyflie API though QT Signal/Slots
        # to avoid manipulating the UI when rendering it
        self._connected_signal.connect(self._connected)
        self._disconnected_signal.connect(self._disconnected)
        self._log_data_signal.connect(self._log_data_received)
        self._param_updated_signal.connect(self._param_updated)

        # UI Buttons Initialise
        self.send_command.clicked.connect(self.ZMQ_Command)

        # Connect the Crazyflie API callbacks to the signals
        self._helper.cf.connected.add_callback(
            self._connected_signal.emit)

        self._helper.cf.disconnected.add_callback(
            self._disconnected_signal.emit)

    def _connected(self, link_uri):
        """Callback when the Crazyflie has been connected"""

        logger.debug("Crazyflie connected to {}".format(link_uri))

        self.Send_Command.setEnabled(True)
        self.console_window.insertPlainText("Connected\n")

        #temp_config = LogConfig("Tempreature", 200)
        #temp_config.add_variable("Temp.C")
        #self._helper.cf.add_config(temp_config)
        #if temp_config.valid:
        #    temp_config.data_recieved_cb.add_callback(self._log_data_signal.emit)
        #    temp_config.start()


    def _disconnected(self, link_uri):
        """Callback for when the Crazyflie has been disconnected"""

        logger.debug("Crazyflie disconnected from {}".format(link_uri))

        self.send_command.setEnabled(False)
        self.console_window.insertPlainText("Disconnected\n")

        # Reset display status values
        self.thrust_val.setText("0")
        self.pitch_val.setText("0")
        self.roll_val.setText("0")
        self.yaw_val.setText("0")

        self.temp_val.setText("0")

        self.X_p.setText("0")
        self.Y_p.setText("0")
        self.Z_p.setText("0")

    def _param_updated(self, name, value):
        """Callback when the registered parameter get's updated"""

        logger.debug("Updated {0} to {1}".format(name, value))

    def _log_data_received(self, timestamp, data, log_conf):
        """Callback when the log layer receives new data"""

        logger.debug("{0}:{1}:{2}".format(timestamp, log_conf.name, data))

        self.temp_c.setText("{0:.2f}C".format(data["temp.C"]))


    def _logging_error(self, log_conf, msg):
        """Callback from the log layer when an error occurs"""

        QMessageBox.about(self, "Error",
                          "Error when using log config"
                          " [{0}]: {1}".format(log_conf.name, msg))

    def ZMQ_Command(self):
        self.progressBar.setValue(0)
        context = zmq.Context()
        sender = context.socket(zmq.PUSH)
        bind_addr = "tcp://127.0.0.1:{}".format(1024 + 188)
        sender.connect(bind_addr)
        Thrust = int(self.thrust_cmd.toPlainText())
        Roll = int(self.roll_cmd.toPlainText())
        Pitch = int(self.pitch_cmd.toPlainText())
        Yaw = int(self.yaw_cmd.toPlainText())

        cmdmess = {
            "version": 1,
            "ctrl": {
                "roll": 0.0,
                "pitch": 0.0,
                "yaw": 0.0,
                "thrust": 0.0
            }
        }
        self.progressBar.setValue(25)

        # Unlocking thrust protection
        cmdmess["ctrl"]["thrust"] = 0
        sender.send_json(cmdmess)

        for i in range(10):
            cmdmess["ctrl"]["thrust"] = Thrust
            sender.send_json(cmdmess)
            time.sleep(0.5)

        self.progressBar.setValue(50)

        for i in range(10):
            Thrust -= Thrust*0.1
            cmdmess["ctrl"]["thrust"] = Thrust
            sender.send_json(cmdmess)
            time.sleep(0.5)

        cmdmess["ctrl"]["thrust"] = 0
        sender.send_json(cmdmess)
        self.progressBar.setValue(100)


