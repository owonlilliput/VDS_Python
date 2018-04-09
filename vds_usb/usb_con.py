from array import array
from collections import namedtuple

import usb.util

INDEX_PRODUCT = 0

PACKAGE_TIMEOUT = 5000

EndPoints = namedtuple('EndPoints', ['r', 'w'])


def usb_find_device(vid=0x5345, pid=0x1234):
    """

    :param vid: int
    :param pid: int
    :return: [] of 'usb.core.Device'
    """
    return usb.core.find(find_all=True, idVendor=vid, idProduct=pid)


def usb_find_endponits(interface):
    """

    :param interface: int
    :return: (epw, epr)
    """
    epw = usb.util.find_descriptor(
        interface,
        # match the first OUT endpoint
        custom_match=(
            lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_OUT)
    )
    epr = usb.util.find_descriptor(
        interface,
        # match the first IN endpoint
        custom_match=(
            lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_IN)
    )
    return EndPoints(epr, epw)


def con_vds(epr, epw):
    sdslver = b':SDSLVER#'
    epw.write(sdslver)
    pre = epr.read(22, timeout=100)
    print(type(pre))
    print(isinstance(pre, bytes))
    print("pre: ", ''.join(chr(i) for i in pre[:-4]))
    data_len = pre[-4:]
    _len = (data_len[0] << 24) + (data_len[1] << 16) + (data_len[2] << 8) + data_len[3]
    print('len: ', _len)
    _content = epr.read(_len)
    print('content: ', ''.join(chr(i) for i in _content))


class USBSource:
    def __init__(self, device, interface=0):
        """

        :param device: 'usb.core.Device'
        :param interface: int
        """
        super(USBSource, self).__init__()
        self.device = device
        self.serialNumber = usb.util.get_string(device, INDEX_PRODUCT)
        # print(self.serialNumber)
        self.interface = interface
        usb.util.claim_interface(device, interface)
        self.eps = self.usb_to_io()

    def usb_to_io(self):
        """

        :return: namedtuple EndPoints
        """
        dev = self.device
        dev.set_configuration()
        cfg = dev.get_active_configuration()
        # print(cfg)
        intf = cfg[(0, 0)]
        # print_all(dev)
        return usb_find_endponits(intf)

    def write(self, b_cmd):
        """

        :param b_cmd: bytes
        :return: int
        """
        return self.eps.w.write(b_cmd)

    def read(self, length):
        rec_arr: array = self.eps.r.read(length, PACKAGE_TIMEOUT)
        # tm = TimeMeasure()
        # tm.start()
        bb = rec_arr.tobytes()
        # tm.stop()
        # print('cost1:', tm.measure)
        return bb

    def close(self):
        usb.util.release_interface(self.device, self.interface)

    def print_all(self):
        for cfg in self.device:
            for i in cfg:
                for e in i:
                    print(e.bEndpointAddress)

    def __str__(self):
        return repr(self) + ' ' + self.serialNumber


if __name__ == '__main__':
    u_dev = next(usb_find_device())
    # print(u_dev)
    dev = USBSource(u_dev)
    dev.write(b':SDSLVER#\n')
    recv = dev.read(1024)
    print(recv)
