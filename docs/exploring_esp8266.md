# Exploring the ESP8266 WiFi module
The ESP8266 module is a small, light-weight and cheap WiFi module based on the ESP8266 chip by Espressif systems. It
features a full TCP/IP stack and micro controller. It can be addressed over a serial interface and requires 3.3V. The
CrazyFlie can provide 3V which should be sufficient in this case.

![ESP8266 ESP-01 WiFi Module](images/300px-ESP-01.jpg)

For this project the ESP-01s version of the ESP8266 module is used, it has 1MB flash and a built-in (PCB) antenna.

## Getting to know the ESP8266 module
Integrating the ESP8266 module in the CrazyFlie is a complex undertaking when unfamiliar with (these) electronics. It
therefore makes sense to get to know the module a bit and understand how to communicate with it outside of the 
CrazyFlie system. To accomplish that, an Arduino Uno was used to power the ESP8266 and provide a serial passthrough
interface so that a PC to ESP8266 serial interface can be set up.

How to connect an Arduino Uno to an ESP8266 can be found online, here [the instructions](https://create.arduino.cc/projecthub/PatelDarshil/how-to-communicate-with-esp8266-via-arduino-uno-f6e92f)
from Patel Darshil on arduino.cc were used to create the setup below:

![ESP8266 connected to Arduino Uno](images/arduino_uno_esp8266_sm.jpg)

The following connectins were made
- Arduino `GND` and `RESET` to ESP8266 `GND`
- Arduino `3.3v` to ESP8266 `VCC` and `CH_PD` (`CH_PD` is the chip powerdown pin, chip will sleep if pin not high) 
- Arduino `RX` to ESP8266 `RX` (pass-through)
- Aruidno `TX` to ESP8266 `TX` (pass-through)

After connecting the Arduino to a PC the red LED on the ESP8266 should turn on. Serial communication with the ESP8266 
is now possible by using the relevant TTY device (check `dmesg`) with a baud rate of 115200, 8N1. The arduino IDE's
Serial Monitor can be easily used for this but `minicom` and `screen` work as well, just remember to send a carriage
return `\r` and newline `\n` after each instruction.

## Talking to the ESP8266
Now that communication with the ESP8266 module is possible, it's time to look at what instructions are useful and
relevant in our context. In short, what is required is to be able to initialize the module, scan the WiFi channels
and get a list of access point (SSID, MAC address) and their signal strength (RSSI). The 4 selected AT instructions below
should suffice for this purpose.

### Relevant AT instructions
Input and output below is indicated with an `I>` and `O>` respectively.

**Test the connection and readiness of the module:**
```
I> AT
O> OK
```

**Set the module's WiFi mode to *station*: (1=station, 2=soft-ap, 3=soft-ap+station)**
```
I> AT+CWMODE=1
O> OK
```

**Set the expected output of a scan:**

Since we are only interested in the `<SSID, RSSI, MAC>` tuple, we limit the output to just those by setting the 2nd,
3rd and 4th bit. (2+4+8)
```
I> AT+CWLAPOPT=0,14
O> OK
```

**Perform a scan over all 802.11g bands**

This takes about 2 seconds to complete. For privacy reasons, the sample below is limited to public access points with
data anonymised.
```
I> AT+CWLAP
O> +CWLAP:(0,"TelenetWiFree",-53,"06:35:3b:00:00:00",1,-9,0)
O> +CWLAP:(0,"TelenetWiFree",-87,"36:2c:b4:00:00:00",1,21,0)
... snip ...
O> +CWLAP:(5,"Proximus Public Wi-Fi",-85,"3a:35:fb:00:00:00",6,10,0)
O> +CWLAP:(0,"TelenetWiFree",-80,"36:2c:b4:00:00:00",11,0,0)
```

## Flashing the ESP8266's firmware
### Motivation
The factory installed firmware on the ESP8266 module is a bit dated and more recent versions are available. You
can see what firmware the module uses by issuing the `AT+GMR` instruction. This was the output for the modules used:
```
I> AT+GMR
O> AT version:1.2.0.0(Jul  1 2016 20:04:45)
O> SDK version:1.5.4.1(39cb9a32)
O> Ai-Thinker Technology Co. Ltd.
O> Dec  2 2016 14:21:16
O> OK
```

While flashing an ESP8266 module can be a cumbersome process, can damage the module and isn't strictly necessary, it 
might still be worth it as it upgrades the `AT version`, among others allowing you to set more options when doing 
`AT+CWLAP`. The 1.5.4 version only allows to set a target `ssid`, `mac` and/or `ch` (channel). 

Newer versions allow to set many more options
like differentiating between active and passive scans, setting the min. and max. time to scan and more. As the 
`AT+CWLAP` is an essential instruction for this project, upgrading the firmware was considered worthwhile.

### Preparation
In order to flash the firmware, the ESP8266 module needs to be able to get into bootmode. To get there, our
Arduino - ESP8266 setup needs some additional connections:
- The `RST` pin needs to be able to be switched between high and low to reset (restart) the module easily.
- The `GPIO0` needs to be able to driven 'low'

It 's probably easiest to connect these 2 pins to a breadboard and connect each one to a push button for easy access. 
More information on the required setup can be found on 
[acoptex.com's page](http://acoptex.com/project/289/basics-project-021b-how-to-update-firmware-esp8266-esp-01-wi-fi-module-at-acoptexcom/#sthash.rrK7eAi3.dpbs)
discussing several different possible setups depending on the tools you have available.

Once the setup is complete, you can
- Download the new firmware from [Espressif's website](https://www.espressif.com/en/support/download/at?keys=&field_type_tid%5B%5D=14) 
- Clone the esptool [GitHub repo](https://github.com/espressif/esptool), a tool provided by Espressif

There is also an application with a GUI available by Espressif, the [Flash Download Tools](https://www.espressif.com/en/support/download/other-tools)
that can be downloaded from their website. This GUI also uses `esptool` underneath, attempts to flash the firmware using
this GUI were unsuccesful however.

### Flashing
The firmware downloaded from Espressif's website was the `ESP8266_NonOS_AT_Bin_V1.7.4` version. Once unpacked,  there
is a README.md in the `bin/at` directory with details on the images and memory addresses to use. Since the ESP8266 comes
with 1MiB flash (= 8Mbit), the `512+512 Nano AT` firmware was used.

The actual flashing was done with the instructions below. For every one of the 5 instructions:
1. Make sure the ESP8266 is running normally
2. Run the instruction, `esptool` will be waiting for bootmode
3. Enter bootmode by driving `GPIO0` low (using the pushbutton) then resetting the module by cycling `RST` (using
the 2nd pushbutton)
4. `esptool` will now copy the image (1 of the 5) to the module's flash

`esptool` instructions including memory addresses:
```
python3 esptool.py --port /dev/ttyACM0 write_flash 0x00000 boot_v1.7.bin 
python3 esptool.py --port /dev/ttyACM0 write_flash 0x01000 user1.1024.new.2.bin 
python3 esptool.py --port /dev/ttyACM0 write_flash 0xfc000 esp_init_data_default_v08.bin 
python3 esptool.py --port /dev/ttyACM0 write_flash 0x7e000 blank.bin 
python3 esptool.py --port /dev/ttyACM0 write_flash 0xfe000 blank.bin 
```
Note that the assigned serial device `/dev/ttyACM0` might differ.

### Result
Results after flashing:

```
I> AT+GMR
O> AT version:1.7.4.0(May 11 2020 19:13:04)
O> SDK version:3.0.4(9532ceb)
O> compile time:May 27 2020 10:12:17
O> Bin version(Wroom 02):1.7.4
O> OK
```
