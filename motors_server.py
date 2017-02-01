import socket
import struct
from time import sleep

audio_bin=4000

TCP_IP = '192.168.0.100'
LEFT_MOTOR_PORT = 5007
RIGHT_MOTOR_PORT = 5008
BUFFER_SIZE = 1024  

s_left = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s_left.bind((TCP_IP, LEFT_MOTOR_PORT))
s_left.listen(1)
s_right = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s_right.bind((TCP_IP, RIGHT_MOTOR_PORT))
s_right.listen(1)

conn_left, addr_left = s_left.accept()
conn_right, addr_right = s_left.accept()

conn_left.send(struct.pack("d", 20.0))
conn_right.send(struct.pack("d", 20.0))

sleep(1)

conn_left.send(struct.pack("d", 100.0))
conn_right.send(struct.pack("d", 100.0))

sleep(1)

conn_left.send(struct.pack("d", -20.0))
conn_right.send(struct.pack("d", -20.0))

sleep(1)

conn_left.send(struct.pack("d", 0.0))
conn_right.send(struct.pack("d", 0.0))

print("disconnected")
conn_left.close()
conn_right.close()
print("all done")
