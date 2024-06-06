class Read:

    def __init__(self):
        self.packet = None
    def read_data(self, port):
        self.packet = port.read_until(b'END')