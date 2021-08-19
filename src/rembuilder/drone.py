import logging
import math
import time

import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig

# Only output errors from the logger.framework
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.utils.power_switch import PowerSwitch

from .utils import ConsolePrinter

# Constants
SCAN_ON_DEMAND = "esp8266.scanOnDemand"
SCAN_INTERVAL = "esp8266.scanInterval"
SCAN_NOW = "esp8266.scanNow"
RADIO_SHUTDOWN_PERIOD = 3

logger = logging.getLogger("rembuilder")


class ScanningDrone:
    def __init__(self, link_uri, initial_x, initial_y, initial_z, initial_yaw):
        self._cf = Crazyflie(rw_cache='./cache')
        self.link = link_uri
        self._initial_x = initial_x
        self._initial_y = initial_y
        self._initial_z = initial_z
        self._initial_yaw = initial_yaw
        self.toc_backup = None
        self.printer = ConsolePrinter(self._cf.console)

        # State
        self.is_connected = False
        self.scan_on_demand = False
        self.scanning = False
        self.position_estimated = False
        self.initial_kalman = {'initialX': False, 'initialY': False, 'initialZ': False, 'initialYaw': False}
        self.dry_run = False

        # Add basic callbacks
        self._cf.connected.add_callback(self._connected)
        self._cf.disconnected.add_callback(self._disconnected)
        self._cf.connection_failed.add_callback(self._connection_failed)
        self._cf.connection_lost.add_callback(self._connection_lost)

        self.printer.start()

        # Try to connect to the Crazyflie
        logger.info(f'Connecting to {link_uri}')
        self._cf.open_link(self.link)

    def _param_updated(self, name: str, value):
        logger.debug(f"Parameter {name} updated to {value}")
        if name == SCAN_ON_DEMAND:
            self.scan_on_demand = bool(int(value))
            logger.debug(f"self.scan_on_demand: {self.scan_on_demand}")
        elif name == SCAN_NOW:
            # TODO: if scan_now already active, reset to 0
            self.scanning = bool(int(value))
            logger.debug(f"self.scanning: {self.scanning}")
            if self.scanning:
                # Disconnect radio to reduce interference, wait a few seconds then reconnect
                logger.info("Shutting down radio while scanning")
                self._cf.close_link()
                time.sleep(RADIO_SHUTDOWN_PERIOD)
                logger.info("Starting radio again")
                self._cf.open_link(self.link)
        elif name.startswith('kalman.initial'):
            self.initial_kalman[name.split('.')[1]] = True

    def _connected(self, *args):
        self._cf.param.add_update_callback(group="esp8266", cb=self._param_updated)
        if not self.scan_on_demand:
            self._cf.param.set_value(SCAN_ON_DEMAND, 1)
        self.is_connected = True

    def _disconnected(self, *args):
        logger.info(f"Disconnected...")

    def _connection_failed(self, *args):
        logger.error(f"Connection failed")

    def _connection_lost(self, *args):
        logger.info(f"Connection lost...")
        # self._cf.open_link(self.link)

    def wait_for_position_estimator(self):
        self.position_estimated = False

        logger.info('Waiting for estimator to find position...')

        log_config = LogConfig(name='Kalman Variance', period_in_ms=500)
        log_config.add_variable('kalman.varPX', 'float')
        log_config.add_variable('kalman.varPY', 'float')
        log_config.add_variable('kalman.varPZ', 'float')

        var_y_history = [1000] * 10
        var_x_history = [1000] * 10
        var_z_history = [1000] * 10

        threshold = 0.001
        counter = 0

        with SyncLogger(self._cf, log_config) as sync_logger:
            for log_entry in sync_logger:
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

                counter += 1

                if (max_x - min_x) < threshold and (
                        max_y - min_y) < threshold and (
                        max_z - min_z) < threshold:
                    logger.info("Position found!")
                    self.position_estimated = True
                    break
                else:
                    logger.debug(f"Tried {counter} times")

    def _set_initial_position(self):
        self._cf.param.set_value('kalman.initialX', self._initial_x)
        self._cf.param.set_value('kalman.initialY', self._initial_y)
        self._cf.param.set_value('kalman.initialZ', self._initial_z)

        yaw_radians = math.radians(self._initial_yaw)
        self._cf.param.set_value('kalman.initialYaw', yaw_radians)

    def _reset_estimator(self):
        self._cf.param.set_value('kalman.resetEstimation', '1')
        time.sleep(0.1)
        self._cf.param.set_value('kalman.resetEstimation', '0')
        self.wait_for_position_estimator()

    def initialize(self):
        # Enable robust TDOA
        self._cf.param.set_value('kalman.robustTdoa', '1')

        # Set initial position
        logger.info("Connected, setting initial position...")
        self._set_initial_position()

        if not self.dry_run:
            self._cf.param.add_update_callback(group="kalman", cb=self._param_updated)
            logger.info('Waiting for position fix...')
            while not all(self.initial_kalman.values()):
                logger.debug(self.initial_kalman)
                time.sleep(0.5)
            self._cf.param.remove_update_callback(group="kalman", cb=self._param_updated)

            self._reset_estimator()

            # Block until we know our (initial) position
            while not self.position_estimated:
                time.sleep(0.5)
        else:
            logger.info("Dry-run active, skipping position fix...")

    def scan_waypoints(self, waypoints):
        for pos_id, position in enumerate(waypoints):
            logger.info(f'Setting waypoint {position[0:3]} and {"scanning" if position[4] else "not scanning"}')

            if not self.dry_run:
                self._goto(
                    self._initial_x + position[0],
                    self._initial_y + position[1],
                    self._initial_z + position[2],
                    self._initial_yaw + position[3]
                )  # blocking

            if position[4]:
                self._access_point_scan()
                while self.scanning:
                    time.sleep(0.2)

    def _goto(self, x, y, z, yaw):
        for _ in range(50):
            self._cf.commander.send_position_setpoint(x, y, z, yaw)
            time.sleep(0.1)

    def _access_point_scan(self):
        # Wait until scan on demand is active (this happens async on connection to Crazyflie)
        while not self.scan_on_demand:
            time.sleep(0.1)

        # Perform a scan
        self._cf.param.set_value(SCAN_NOW, 1)
        while not self.scanning:
            time.sleep(0.1)

    def shutdown(self):
        # Land the Crazyflie
        self._cf.commander.send_stop_setpoint()

        # Close thread and link and USB radio
        self.printer.stop = True
        self._cf.close_link()
        cflib.crtp.get_link_driver(self.link).close()
        time.sleep(5)

        # Power down the CF
        try:
            ps = PowerSwitch(self.link)
            ps.platform_power_down()
        except:
            pass
