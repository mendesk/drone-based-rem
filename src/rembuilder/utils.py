from datetime import datetime
import logging
import re
import time

from threading import Thread, Lock
from typing import List

# Regexes for parsing output
PTN_CWLAP = re.compile(r'^AT\+CWLAP(=\d*,\d*,\d*,\d*,\d*,\d*)?$')
PTN_POS = re.compile(r'^POS: x=([+-]?\d+\.\d+) y=([+-]?\d+\.\d+) z=([+-]?\d+\.\d+)$')
PTN_BEGIN = re.compile(r'^ESP8266: -- START READING --$')
PTN_AP = re.compile(r'^AP: (?P<ssid>.*), (?P<rssi>-?\d+), (?P<mac>\w+), (?P<chn>\d+)$')
PTN_END = re.compile(r'^ESP8266: -- STOP READING --$')
# PTN_POS = re.compile(r'^POS: (?:[xyz]=([+-]?\d+\.\d+)\s){3}$')

logger = logging.getLogger("rembuilder")


class Measurement:
    obfuscate_mac_address = False

    def __init__(self, timestamp: datetime, x: float, y: float, z: float, ssid: str, rssi: int, mac: str, chn: int):
        self.timestamp = timestamp
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.ssid = str(ssid)
        self.rssi = int(rssi)
        self.mac = str(mac).rjust(12, '0')
        self.chn = int(chn)

    def normalized_signal_strength(self) -> float:
        # 802.11 rssi from -10 (strongest) to -100 (weakest), normalized to a value in the interval [0, 1], closer
        # to one means a stronger signal
        return (self.rssi + 100) / 90

    def get_mac(self) -> str:
        if Measurement.obfuscate_mac_address:
            return self.mac[:6] + 6 * '-'
        else:
            return self.mac

    def __repr__(self):
        return f"{self.timestamp.isoformat()};{self.x};{self.y};{self.z};" \
               f"{self.ssid};{self.rssi};{self.get_mac()};{self.chn}"


class ConsolePrinter(Thread):
    def __init__(self, console):
        super().__init__()

        self.buffer = ""
        self.buffer_lock = Lock()
        self.stop = False
        self.ap_list: List[Measurement] = []
        self.last_parsed_position = (None, None, None)

        # Register callbacks
        console.receivedChar.add_callback(self.cb_append_to_console)

        # Matching status
        self.reading_phase = False
        self.pos_known_phase = False
        self.cwlap_phase = False

        # Match tracking
        self.cwlap_start_time = None
        self.cwlap_result_count = 0

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
                    logger.debug(f'CF: {line}')
                    self.buffer = self.buffer[pos+1:]
                    self.parse_line(line)
            time.sleep(0.2)

        # Write results to file
        logger.info(f"Collected {len(self.ap_list)} measurements. Writing to file...")
        filename = datetime.now().strftime('%Y%m%d_%H%M%S') + "_rembuilder.out"
        with open("output/" + filename, 'w') as fh:
            fh.write("time;x;y;z;ssid;rssi;mac;channel\n")
            for ap in self.ap_list:
                fh.write(str(ap) + '\n')
        logger.info(f"Results written to {filename}")

        for ap in self.ap_list:
            # print(*ap, flush=True)
            logger.debug(ap)

    def parse_line(self, line):
        if not self.cwlap_phase:
            mo = PTN_CWLAP.match(line)
            if mo is not None:
                logger.debug("REGEX: self.cwlap_phase = True")
                self.cwlap_phase = True
                self.cwlap_start_time = datetime.utcnow()
                self.cwlap_result_count = 0
        elif not self.pos_known_phase:
            mo = PTN_POS.match(line)
            if mo is not None:
                self.last_parsed_position = mo.groups()
                logger.debug("REGEX: self.pos_known_phase = True")
                self.pos_known_phase = True
        elif not self.reading_phase:
            mo = PTN_BEGIN.match(line)
            if mo is not None:
                logger.debug("REGEX: self.reading_phase = True")
                self.reading_phase = True
        else:
            mo = PTN_AP.match(line)
            if mo is not None:
                logger.debug("REGEX: AP found")
                # self.ap_list.append((self.cwlap_start_time.isoformat(), *self.last_parsed_position, *mo.groups()))
                self.ap_list.append(
                    Measurement(
                        self.cwlap_start_time,
                        x=float(self.last_parsed_position[0]),
                        y=float(self.last_parsed_position[1]),
                        z=float(self.last_parsed_position[2]),
                        ssid=mo.group('ssid'),
                        rssi=int(mo.group('rssi')),
                        mac=mo.group('mac'),
                        chn=int(mo.group('chn'))
                    )
                )
                self.cwlap_result_count += 1
            else:
                mo = PTN_END.match(line)
                if mo is not None:
                    logger.debug("REGEX: self.cwlap_phase = False")
                    logger.info(f"{self.cwlap_result_count} access points found")
                    self.cwlap_phase = False
                    self.pos_known_phase = False
                    self.reading_phase = False
                    self.cwlap_start_time = None
                    self.cwlap_result_count = 0
