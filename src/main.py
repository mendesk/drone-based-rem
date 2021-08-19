from datetime import datetime
import logging
import time

import cflib.crtp  # noqa
from rembuilder.drone import ScanningDrone

logging.getLogger("cflib").setLevel(logging.ERROR)
logger = logging.getLogger("rembuilder")
logger.setLevel(logging.DEBUG)
cf = logging.Formatter('%(message)s')
ff = logging.Formatter('%(asctime)s [%(name)s] [%(levelname)s] %(message)s')
# formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(cf)
ch.setLevel(logging.INFO)
logger.addHandler(ch)
fhd = logging.FileHandler("output/" + datetime.now().strftime('%Y%m%d_%H%M%S') + "_rembuilder_console_debug.out")
fhd.setFormatter(ff)
fhd.setLevel(logging.DEBUG)
logger.addHandler(fhd)
fhi = logging.FileHandler("output/" + datetime.now().strftime('%Y%m%d_%H%M%S') + "_rembuilder_console.out")
fhi.setFormatter(ff)
fhi.setLevel(logging.INFO)
logger.addHandler(fhi)

# Volume Dimensions
# x: 0m -> 2,20m
# y: 0m -> 4,25m
# z: 0m -> 2,00m
starting_point = (1.59, 1.08, -0.20, 0)

start_x = 1.59
start_y = 1.08
start_z = -0.05
start_yaw = 0  # In degrees

"""sequence = [
    # Grid at 0.5m above start_z
    (0, 0, 0.5, 0),
    (-0.4, 0, 0.5, 0),
    (-0.4, 0.4, 0.5, 0),
    (0, 0.4, 0.5, 0),
    (0.4, 0.4, 0.5, 0),
    (0.4, 0.0, 0.5, 0),
    (0.4, -0.4, 0.5, 0),
    # (0.4, -0.8, 0.5, 0),
    # (0, -0.8, 0.5, 0),
    # (-0.4, -0.8, 0.5, 0),
    (0, -0.4, 0.5, 0),
    (-0.4, -0.4, 0.5, 0),
    (0, 0.5, 0.5, 0),
    # Go home
    (0, 0, 0.35, 0),
]
"""
# sequence = [
#     # Grid at 0.5m above start_z
#     # (relative x, relative, relative z, relative yaw, scan)
#     (0, 0, 0.4, 0, False),  # take-off
#
#     (-0.5, -0.8, 0.4, 0, True),
#     (-0.5, -0.2, 0.4, 0, True),
#     (-0.5, 0.2, 0.4, 0, True),
#     (0, 0.2, 0.4, 0, True),
#     (0.5, 0.2, 0.4, 0, True),
#     (0.5, -0.2, 0.4, 0, True),
#     (0.5, -0.8, 0.4, 0, True),
#     (0, -0.8, 0.4, 0, True),
#
#     (-0.5, -0.8, 0.8, 0, True),
#     (-0.5, -0.2, 0.8, 0, True),
#     (-0.5, 0.2, 0.8, 0, True),
#     (0, 0.2, 0.8, 0, True),
#     (0.5, 0.2, 0.8, 0, True),
#     (0.5, -0.2, 0.8, 0, True),
#     (0.5, -0.8, 0.8, 0, True),
#     (0, -0.8, 0.8, 0, True),
#
#     # (0, 0, 0.5, 0, False),  # prepare landing
#     (0, 0, 0.15, 0, False),  # prepare landing
# ]

# sequence = [
#     # Grid at 0.5m above start_z
#     # (relative x, relative, relative z, relative yaw, scan)
#     (0, 0, 0.4, 0, False),  # take-off
#
#     (-0.5, -0.8, 0.4, 0, True),
#     (-0.5, -0.2, 0.4, 0, True),
#     (-0.5, 0.2, 0.4, 0, True),
#     (0, 0.2, 0.4, 0, True),
#     (0.5, 0.2, 0.4, 0, True),
#     (0.5, -0.2, 0.4, 0, True),
#     (0.5, -0.8, 0.4, 0, True),
#     (0, -0.8, 0.4, 0, True),
#
#     (0, 0, 0.4, 0, False),  # prepare landing
#     (0, 0, 0.25, 0, False),  # prepare landing
# ]
#
#Test sequence
sequence = [
    (0, 0, 0.3, 0, True),  # take-off
    (0, -0.3, 0.3, 0, True),
    (0, 0, 0.3, 0, True),
    (0.3, 0, 0.3, 0, True),
    (0.3, 0, 0.15, 0, False),
]

if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    available = []
    for i in range(3):
        # Scan for Crazyflies and use the first one found
        logger.info('Scanning interfaces for Crazyflies...')
        available = cflib.crtp.scan_interfaces()
        if len(available):
            logger.info('Crazyflies found:')
            for cf in available:
                logger.info(cf[0])
            break

    if len(available) == 0:
        raise SystemExit("No Crazyflie found")

    logger.info("Connecting to first available Crazyflie")
    drone = ScanningDrone(available[0][0], start_x, start_y, start_z, start_yaw)
    # drone.dry_run = True
    while not drone.is_connected:
        time.sleep(0.1)

    drone.initialize()
    drone.scan_waypoints(sequence)
    drone.shutdown()
