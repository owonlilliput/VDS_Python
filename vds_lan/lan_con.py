from socket import AF_INET, socket, SOCK_STREAM, setdefaulttimeout

PACKAGE_SIZE = 40960

PACKAGE_TIMEOUT = 5


class LanSource:
    def __init__(self, address):
        """

        :param address: (ip, port) -> (str, int)
        """
        super(LanSource, self).__init__()
        setdefaulttimeout(5)
        client = socket(AF_INET, SOCK_STREAM)
        client.connect(address)
        client.settimeout(PACKAGE_TIMEOUT)
        self.address = address
        self.client = client

    def write(self, b_cmd):
        sent = self.client.send(b_cmd)
        return sent

    def _read(self, length):
        rd = self.client.recv(length)
        # print(rd)
        return rd

    def close(self):
        self.client.close()

    def __str__(self):
        return repr(self) + ' ' + str(self.address)

    def read(self, length):
        if length < 0:
            return self._read(1024)

        received = b''
        while length:
            recv = self._read(length)
            print(len(recv), end=',')
            received = received + recv
            length = length - len(recv)

        print()
        return received


if __name__ == '__main__':
    ls = LanSource(('192.168.1.60', 2000))
    ls.write(b':SDSLVER#')
    print(ls.read(-1))
    ls.close()
