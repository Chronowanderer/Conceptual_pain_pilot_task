from PyDAQmx import *
from ctypes import *
import numpy as np
import time
import socket


CODE_TESTING = False

HOST = "127.0.0.1"
PORT = 60000
DEVICE = [b'Dev1']
CHANNEL = [b'ao0', b'ao1']


class ElectricShock(Task):
    def __init__(self, outName, bodyPart, shockDuration, startTime):
        Task.__init__(self)
        self.start = startTime

        # Pulse Setting Code
        self.temporalGap = 0.5  # Temporal gap between colliding and shocking (sec)

        # Stimulation Setting Code
        self.shockIntensity = 5
        self.stim = [0] * 1 + [self.shockIntensity] * 3 + [0] * 1  # Stimulus
        # self.stim = [0] * 5 + [self.shockIntensity] * 10 + [0] * 5
        self.stim = self.stim * 10  # x10 in 50ms, 200Hz
        self.stim = np.array(self.stim, dtype = np.float64)
        self.zerostim = np.zeros(len(self.stim))

        # Shock Input Setting
        self.bodyPart = bodyPart
        self.shockDuration = shockDuration
        self.outName = outName

        # Shock Task Setting
        self.CreateAOVoltageChan(self.outName, '', -10.0, 10.0, DAQmx_Val_Volts, None)
        self.sampsWritten = int32()


    def Shock(self):
        # Task Configure Code
        if self.shockDuration > 0:
            time.sleep(self.temporalGap)
            # self.CfgSampClkTiming("", 1000, DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, len(self.stim))
            self.WriteAnalogF64(len(self.stim), True, 10.0, DAQmx_Val_GroupByChannel, self.stim,
                                byref(self.sampsWritten), None)
            print("DAQhardware.writeValue(): chanNames = %s val = %s" % (repr(self.outName), repr(self.stim)))
        else:
            self.WriteAnalogF64(len(self.stim), True, 10.0, DAQmx_Val_GroupByChannel, self.zerostim,
                                byref(self.sampsWritten), None)
            print("DAQhardware.writeValue(): chanNames = %s val = %s" % (repr(self.outName), repr(self.zerostim)))

        # Print for debug
        print("DAQhardware.setupAnalogOutput(): Wrote %d samples" % self.sampsWritten.value)
        print("Task duration: %.3f sec" % (time.time() - self.start))


class SocketConnection:
    def __init__(self, host, port):
        self.address = (host, port)

    def connect(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(self.address)
        server.listen(5)
        try:
            connectionFlag = False
            while True:
                if not connectionFlag:
                    clientsocket, _ = server.accept()
                connectionFlag = self.read_from_client(clientsocket)
                if not connectionFlag:
                    clientsocket.close()
        except IOError as e:
            print(e.strerror)

    def read_from_client(self, clientsocket):
        content = None
        try:
            input = clientsocket.recv(1024)
            if input:
                content = input.decode('ascii')
        except IOError as e:
            print(e.strerror)
        if content:
            data = content.strip().split(' ')
            bodyPart, shockDuration = int(data[0]), float(data[1])
            print('Input: ', bodyPart, ' ', shockDuration)

            # DAQmx Configure Code
            for devName in DEVICE:
                outName = devName + b'/' + CHANNEL[bodyPart]
                task = ElectricShock(outName, bodyPart, shockDuration, time.time())
                task.StartTask()
                task.Shock()
                task.StopTask()
                task.ClearTask()

            return True
        else:
            return False


def Test(bodyPart, shockDuration):
    outName = DEVICE[0] + b'/' + CHANNEL[bodyPart]
    task = ElectricShock(outName, bodyPart, shockDuration, time.time())
    task.StartTask()
    task.Shock()
    task.StopTask()
    task.ClearTask()


if __name__ == "__main__":
    if CODE_TESTING:
        Test(0, 100)
    else:
        SocketConnection(HOST, PORT).connect()
