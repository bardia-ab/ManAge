import sys
import time, serial
from pathlib import Path
from datetime import datetime
##########################
def decode(byte):
    byte, period = int(f'{byte:08b}'[1:], 2), f'{byte:08b}'[0]

    if byte == 0x5f:
        char = '0'
    elif byte == 0x06:
        char = '1'
    elif byte == 0x6b:
        char = '2'
    elif byte == 0x2f:
        char = '3'
    elif byte == 0x36:
        char = '4'
    elif byte == 0x3d:
        char = '5'
    elif byte == 0x7d:
        char = '6'
    elif byte == 0x07:
        char = '7'
    elif byte == 0x7f:
        char = '8'
    elif byte == 0x3f:
        char = '9'
    else:
        exit()

    return char, period

##########################

COM_port = sys.argv[1]
csv_file_path = sys.argv[2]
baud_rate = 9600
port = serial.Serial(COM_port, baud_rate)
port.flushInput()
print(port.name)

line = bytearray()
if not Path(csv_file_path).is_file():
    file = open(csv_file_path, 'w+')
    file.write('Current,current_time,current_date\n')

while True:
    file = open(csv_file_path, 'a+')
    byte = port.read(size=1)
    if byte:
        line += byte

    if line[-6:].hex().encode('Ascii') == b'aa5552240110':
        packet = port.read(4)
        value = []
        for i in range(4):
            char, period = decode(packet[i])
            value.insert(0, char)
            if i == 2:
                value.insert(0, '.')

        value = ''.join(value)
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        current_date = datetime.now().date()
        file.write(f'{value},{current_time},{str(current_date)}\n')
        file.close()

port.close()
file.close()