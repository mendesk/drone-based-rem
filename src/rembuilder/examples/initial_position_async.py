import logging
import math
import re
import sys
import time
from threading import Timer, Thread, Lock

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig

# Only output errors from the logging framework
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.utils.power_switch import PowerSwitch

logging.basicConfig(level=logging.ERROR)

# Constants
SCAN_ON_DEMAND = "esp8266.scanOnDemand"
SCAN_INTERVAL = "esp8266.scanInterval"
SCAN_NOW = "esp8266.scanNow"
RADIO_SHUTDOWN_PERIOD = 5

# Regexes for parsing output
PTN_CWLAP = re.compile(r'^AT\+CWLAP$')
PTN_POS = re.compile(r'^POS: x=([+-]?\d+\.\d+) y=([+-]?\d+\.\d+) z=([+-]?\d+\.\d+)$')
PTN_BEGIN = re.compile(r'^ESP8266: -- START READING --$')
PTN_AP = re.compile(r'^AP: (?P<ssid>.*), (?P<rssi>-?\d+), (?P<mac>\w+), (?P<chn>\d+)$')
PTN_END = re.compile(r'^ESP8266: -- STOP READING --$')
# PTN_POS = re.compile(r'^POS: (?:[xyz]=([+-]?\d+\.\d+)\s){3}$')


class ConsolePrinter(Thread):
    def __init__(self, console):
        super().__init__()

        self.buffer = ""
        self.buffer_lock = Lock()
        self.stop = False
        self.ap_list = []
        self.last_parsed_position = (None, None, None)

        # Register callbacks
        console.receivedChar.add_callback(self.cb_append_to_console)

        # Matching status
        self.reading_phase = False
        self.pos_known_phase = False
        self.cwlap_phase = False

    def cb_append_to_console(self, text):
        with self.buffer_lock:
            self.buffer += text

    def run(self) -> None:
        while not self.stop:
            while 1:
                with self.buffer_lock:
                    pos = self.buffer.find('\n')
                    if pos < 0:
                        break
                    line = self.buffer[:pos].rstrip('\r\n')
                    print(f'CF: {line}', flush=True)
                    self.buffer = self.buffer[pos+1:]
                    self.parse_line(line)
            time.sleep(0.2)

        print(f"\nCollected {len(self.ap_list)} Access Points:")
        for ap in self.ap_list:
            print(*ap, flush=True)

    def parse_line(self, line):
        if not self.cwlap_phase:
            mo = PTN_CWLAP.match(line)
            if mo is not None:
                logging.debug("REGEX: self.cwlap_phase = True")
                self.cwlap_phase = True
        elif not self.pos_known_phase:
            mo = PTN_POS.match(line)
            if mo is not None:
                self.last_parsed_position = mo.groups()
                logging.debug("REGEX: self.pos_known_phase = True")
                self.pos_known_phase = True
        elif not self.reading_phase:
            mo = PTN_BEGIN.match(line)
            if mo is not None:
                logging.debug("REGEX: self.reading_phase = True")
                self.reading_phase = True
        else:
            mo = PTN_AP.match(line)
            if mo is not None:
                logging.debug("REGEX: AP found")
                self.ap_list.append((*self.last_parsed_position, *mo.groups()))
            else:
                mo = PTN_END.match(line)
                if mo is not None:
                    logging.debug("REGEX: self.cwlap_phase = False")
                    self.cwlap_phase = False
                    self.pos_known_phase = False
                    self.reading_phase = False


class WifiScanner:
    def __init__(self, link_uri):
        self._cf = Crazyflie(rw_cache='./cache')
        self.link = link_uri
        self.toc_backup = None
        self.printer = ConsolePrinter(self._cf.console)

        self.scan_on_demand = False
        self.scanning = False

        # Add basic callbacks
        self._cf.connected.add_callback(self._connected)
        self._cf.disconnected.add_callback(self._disconnected)
        self._cf.connection_failed.add_callback(self._connection_failed)
        self._cf.connection_lost.add_callback(self._connection_lost)

        self.printer.start()

        # Try to connect to the Crazyflie
        print(f'Connecting to {link_uri}')
        self._cf.open_link(self.link)

        # Variable used to keep main loop occupied until disconnect
        self.is_connected = True


    def wait_for_position_estimator(self):
        print('Waiting for estimator to find position...')

        log_config = LogConfig(name='Kalman Variance', period_in_ms=500)
        log_config.add_variable('kalman.varPX', 'float')
        log_config.add_variable('kalman.varPY', 'float')
        log_config.add_variable('kalman.varPZ', 'float')

        var_y_history = [1000] * 10
        var_x_history = [1000] * 10
        var_z_history = [1000] * 10

        threshold = 0.001

        with SyncLogger(self._cf, log_config) as logger:
            for log_entry in logger:
                data = log_entry[1]

                var_x_history.append(data['kalman.varPX'])
                var_x_history.pop(0)
                var_y_history.append(data['kalman.varPY'])
                var_y_history.pop(0)
                var_z_history.append(data['kalman.varPZ'])
                var_z_history.pop(0)

                min_x = min(var_x_history)
                max_x = max(var_x_history)
                min_y = min(var_y_history)
                max_y = max(var_y_history)
                min_z = min(var_z_history)
                max_z = max(var_z_history)

                # print("{} {} {}".
                #       format(max_x - min_x, max_y - min_y, max_z - min_z))

                if (max_x - min_x) < threshold and (
                        max_y - min_y) < threshold and (
                        max_z - min_z) < threshold:
                    break


    def set_initial_position(self, x, y, z, yaw_deg):
        self._cf.param.set_value('kalman.initialX', x)
        self._cf.param.set_value('kalman.initialY', y)
        self._cf.param.set_value('kalman.initialZ', z)

        yaw_radians = math.radians(yaw_deg)
        self._cf.param.set_value('kalman.initialYaw', yaw_radians)


    def reset_estimator(self):
        cf = self._cf
        cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        cf.param.set_value('kalman.resetEstimation', '0')
        self.wait_for_position_estimator()


    def _toc_refreshed(self, *args):
        print("TOC Refreshed")
        for arg in args:
            print(f"  {arg}")
        self._toc_available = True


    def _param_updated(self, name: str, value):
        print(f"Parameter {name} updated to {value}")
        if name == SCAN_ON_DEMAND:
            self.scan_on_demand = bool(int(value))
            print(f"self.scan_on_demand: {self.scan_on_demand}")
        elif name == SCAN_NOW:
            self.scanning = bool(int(value))
            print(f"self.scanning: {self.scanning}")
            if self.scanning:
                # Disconnect radio to reduce interference, wait a few seconds then reconnect
                print("Pausing radio while scanning")
                # self._cf.close_link()
                self._cf.link.pause()
                time.sleep(RADIO_SHUTDOWN_PERIOD)
                print("Restarting radio")
                # self._cf.open_link(self.link)
                self._cf.link.restart()
        elif name.startswith("flightmode"):
            print(f"Parameter {name} changed to {value}")


    def _connected(self, *args):
        print("Connected, scan on demand...")
        # self._cf.param.add_update_callback(group="esp8266", cb=self._param_updated)
        # if not self.scan_on_demand:
        #     self._cf.param.set_value(SCAN_ON_DEMAND, 1)


    def _disconnected(self, *args):
        print(f"Disconnected...")


    def _connection_failed(self, *args):
        print(f"Connection failed")


    def _connection_lost(self, *args):
        print(f"Connection lost...")


    def access_point_scan(self):
        # Wait until scan on demand is active
        # while not self.scan_on_demand:
        #     time.sleep(0.5)

        # Perform a scan
        # self._cf.param.set_value(SCAN_NOW, 1)
        # while not self.scanning:
        #     time.sleep(1)



    def shutdown(self):
        # Close thread and link and USB radio
        self.printer.stop = True
        self._cf.close_link()
        cflib.crtp.get_link_driver(self.link).close()
        time.sleep(5)

        # Power down the CF
        # ps = PowerSwitch(self.link)
        # ps.platform_power_down()


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    # Scan for Crazyflies and use the first one found
    print('Scanning interfaces for Crazyflies...')
    available = cflib.crtp.scan_interfaces()
    print('Crazyflies found:')
    for i in available:
        print(i[0])

    if len(available) > 0:
        drone = WifiScanner(available[0][0])
        drone.wait_for_position_estimator()

        drone.access_point_scan()

        time.sleep(10)
        drone.access_point_scan()

        time.sleep(10)
        print("Shutting down")
        drone.shutdown()
    else:
        print('No Crazyflies found!')
        raise SystemExit(1)
