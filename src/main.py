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
# x: 0m -> 3.74m
# y: 0m -> 2.30m
# z: 0m -> 2,10m

# TEST SEQUENCE
# drones = [
#     {  # Drone 1
#         "uri": "radio://0/80/2M",
#         "start_x": 1.87,
#         "start_y": 1.15,
#         "start_z": -0.19,
#         "start_yaw": 45,  # In degrees
#         "sequence": [
#             (0, 0, 0.75, 0, True),  # take-off
#             (0, -0.3, 0.75, 0, True),
#             (0, 0, 0.75, 0, True),
#             (0.3, 0, 0.75, 0, True),
#             (0, 0, 0.75, 0, True),
#             (0, 0, 0.25, 0, False),
#         ],
#     },
#     {  # Drone 2
#         "uri": "radio://0/80/2M/E8E8E8E8E8",
#         "start_x": 1.37,
#         "start_y": 1.15,
#         "start_z": -0.19,
#         "start_yaw": 45,  # In degrees
#         "sequence": [
#             (0, 0, 0.75, 0, True),  # take-off
#             (0, -0.3, 0.75, 0, True),
#             (0, 0, 0.75, 0, True),
#             (0.3, 0, 0.75, 0, True),
#             (0, 0, 0.75, 0, True),
#             (0, 0, 0.25, 0, False),
#         ],
#     }
# ]

# DATA SEQUENCE
drones = [
    {  # Drone 1
        "uri": "radio://0/80/2M",
        "start_x": 2.10,
        "start_y": 0.15,
        "start_z": -0.20,
        "start_yaw": 45,  # In degrees
        "sequence": [
            # Bottom layer
            (0.00, 0.00, 0.70, 0.00, True),  # take-off
            (0.00, 0.50, 0.70, 0.00, True),
            (0.50, 0.50, 0.70, 0.00, True),
            (0.50, 1.00, 0.70, 0.00, True),
            (0.00, 1.00, 0.70, 0.00, True),
            (0.00, 1.50, 0.70, 0.00, True),
            (0.50, 1.50, 0.70, 0.00, True),
            (1.00, 1.50, 0.70, 0.00, True),
            (1.00, 1.00, 0.70, 0.00, True),
            (1.00, 0.50, 0.70, 0.00, True),
            (1.00, 0.00, 0.70, 0.00, True),
            (0.50, 0.00, 0.70, 0.00, True),
            # Mid layer
            (0.00, 0.00, 1.20, 0.00, True),
            (0.00, 0.50, 1.20, 0.00, True),
            (0.50, 0.50, 1.20, 0.00, True),
            (0.50, 1.00, 1.20, 0.00, True),
            (0.00, 1.00, 1.20, 0.00, True),
            (0.00, 1.50, 1.20, 0.00, True),
            (0.50, 1.50, 1.20, 0.00, True),
            (1.00, 1.50, 1.20, 0.00, True),
            (1.00, 1.00, 1.20, 0.00, True),
            (1.00, 0.50, 1.20, 0.00, True),
            (1.00, 0.00, 1.20, 0.00, True),
            (0.50, 0.00, 1.20, 0.00, True),
            # Top layer
            (0.00, 0.00, 1.70, 0.00, True),
            (0.00, 0.50, 1.70, 0.00, True),
            (0.50, 0.50, 1.70, 0.00, True),
            (0.50, 1.00, 1.70, 0.00, True),
            (0.00, 1.00, 1.70, 0.00, True),
            (0.00, 1.50, 1.70, 0.00, True),
            (0.50, 1.50, 1.70, 0.00, True),
            (1.00, 1.50, 1.70, 0.00, True),
            (1.00, 1.00, 1.70, 0.00, True),
            (1.00, 0.50, 1.70, 0.00, True),
            (1.00, 0.00, 1.70, 0.00, True),
            (0.50, 0.00, 1.70, 0.00, True),
            # Landing
            (0.00, 0.00, 1.20, 0.00, False),
            (0.00, 0.00, 0.60, 0.00, False),
            (0.00, 0.00, 0.25, 0.00, False),
        ],
    },
    {  # Drone 2
        "uri": "radio://0/80/2M/E8E8E8E8E8",
        "start_x": 0.60,
        "start_y": 0.15,
        "start_z": -0.20,
        "start_yaw": 45,  # In degrees
        "sequence": [
            # Bottom layer
            (0.00, 0.00, 0.70, 0.00, True),  # take-off
            (0.00, 0.50, 0.70, 0.00, True),
            (0.50, 0.50, 0.70, 0.00, True),
            (0.50, 1.00, 0.70, 0.00, True),
            (0.00, 1.00, 0.70, 0.00, True),
            (0.00, 1.50, 0.70, 0.00, True),
            (0.50, 1.50, 0.70, 0.00, True),
            (1.00, 1.50, 0.70, 0.00, True),
            (1.00, 1.00, 0.70, 0.00, True),
            (1.00, 0.50, 0.70, 0.00, True),
            (1.00, 0.00, 0.70, 0.00, True),
            (0.50, 0.00, 0.70, 0.00, True),
            # Mid layer
            (0.00, 0.00, 1.20, 0.00, True),
            (0.00, 0.50, 1.20, 0.00, True),
            (0.50, 0.50, 1.20, 0.00, True),
            (0.50, 1.00, 1.20, 0.00, True),
            (0.00, 1.00, 1.20, 0.00, True),
            (0.00, 1.50, 1.20, 0.00, True),
            (0.50, 1.50, 1.20, 0.00, True),
            (1.00, 1.50, 1.20, 0.00, True),
            (1.00, 1.00, 1.20, 0.00, True),
            (1.00, 0.50, 1.20, 0.00, True),
            (1.00, 0.00, 1.20, 0.00, True),
            (0.50, 0.00, 1.20, 0.00, True),
            # Top layer
            (0.00, 0.00, 1.70, 0.00, True),
            (0.00, 0.50, 1.70, 0.00, True),
            (0.50, 0.50, 1.70, 0.00, True),
            (0.50, 1.00, 1.70, 0.00, True),
            (0.00, 1.00, 1.70, 0.00, True),
            (0.00, 1.50, 1.70, 0.00, True),
            (0.50, 1.50, 1.70, 0.00, True),
            (1.00, 1.50, 1.70, 0.00, True),
            (1.00, 1.00, 1.70, 0.00, True),
            (1.00, 0.50, 1.70, 0.00, True),
            (1.00, 0.00, 1.70, 0.00, True),
            (0.50, 0.00, 1.70, 0.00, True),
            # Landing
            (0.00, 0.00, 1.20, 0.00, False),
            (0.00, 0.00, 0.60, 0.00, False),
            (0.00, 0.00, 0.25, 0.00, False),
        ],
    }
]


if __name__ == '__main__':
    # Initialize the low-level drivers (don't list the debug drivers)
    cflib.crtp.init_drivers(enable_debug_driver=False)

    # Initialize drones
    for drone in drones:
        scanning_drone = ScanningDrone(
            drone["uri"],
            drone["start_x"],
            drone["start_y"],
            drone["start_z"],
            drone["start_yaw"]
        )

        # drone.dry_run = True
        while not scanning_drone.is_connected:
            time.sleep(0.1)

        scanning_drone.initialize()
        scanning_drone.scan_waypoints(drone["sequence"])
        scanning_drone.shutdown()
