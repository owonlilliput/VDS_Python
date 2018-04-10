import time
from collections import namedtuple
from functools import reduce
from struct import pack, unpack

from vds_usb.usb_con import usb_find_device, USBSource

import numpy as np
import matplotlib.pyplot as plt

WaveFormInfo = namedtuple('WaveFormInfo',
                          ['len', 'name', 'data_len', 'freq', 'ref', 'start', 'screenlen', 'slow'])

WaveForm = namedtuple('WaveForm',
                      ['waveform_info', 'data'])

WaveFormMemInfo = namedtuple('WaveFormMemInfo',
                             ['name', 'data_len', 'freq', 'ref', 'start', 'screenlen', 'slow'])

WaveFormMem = namedtuple('WaveFormMem',
                         ['waveform_mem_info', 'data'])

MEM_BUFFER_SIZE = 16384
CHANNEL_NUMBER = 4


def print_array(buf):
    for b in buf:
        if ord('0') <= b <= ord('z'):
            b = chr(b)
        print(b, end=',')
    print()


def collect_cmds():
    buffers = []

    def append(buf):
        buffers.append(buf)
        print_array(buf)

    pack_cmds(append)

    cmd_buf = b''
    for buf in buffers:
        cmd_buf = cmd_buf + buf

    cmd_len = len(cmd_buf)
    fmt = '>2si' + str(cmd_len) + 's'
    print(fmt)
    cmd_buf = pack(fmt, b':M', cmd_len, cmd_buf)
    print(cmd_buf)
    return cmd_buf


def pack_cmds(append):
    """

    :param append:
    :return:
    """
    ''' 
    M,D,P,1,
    '''

    # dev_src.write(pack('>2si3sB', b':M', 4, b'MDP', 1))
    mem = 3
    buf = pack('>3sB', b'MDP', mem)
    append(buf)

    '''
    M, T, R, s, 0, e, 2, 0,
    M, T, R, s, 0, e, 3, 0,
    M, T, R, s, 0, e, 5, 0,
    M, T, R, s, 0, e, 4, 0, 0, 0, 1,
    M, T, R, s, 0, e, 6, 0, 0, 0, 2,
    '''
    buf = pack('>3sBBBBB', b'MTR', ord('s'), 0, ord('e'), 2, 0)
    append(buf)
    buf = pack('>3sBBBBB', b'MTR', ord('s'), 0, ord('e'), 3, 0)
    append(buf)
    buf = pack('>3sBBBBB', b'MTR', ord('s'), 0, ord('e'), 5, 0)
    append(buf)
    buf = pack('>3sBBBBi', b'MTR', ord('s'), 0, ord('e'), 4, 1)
    append(buf)
    buf = pack('>3sBBBBi', b'MTR', ord('s'), 0, ord('e'), 6, 2)
    append(buf)

    '''
    M,C,H,0,o,1,
    M,C,H,0,c,1,
    M,C,H,0,v,5,
    M,C,H,0,z,0,0,0,2,
    M,C,H,0,b,0,
    '''
    zero = 00
    for chl in range(CHANNEL_NUMBER):
        buf = pack('>3sBBB', b'MCH', chl, ord('o'), 1)
        append(buf)
        buf = pack('>3sBBB', b'MCH', chl, ord('c'), 1)
        append(buf)
        buf = pack('>3sBBB', b'MCH', chl, ord('v'), 5)
        append(buf)
        buf = pack('>3sBBi', b'MCH', chl, ord('z'), zero)
        append(buf)
        buf = pack('>3sBBB', b'MCH', chl, ord('b'), 0)
        append(buf)
        zero = zero + 10

    '''
    M,A,Q,0,
    M,S,Y,O,U,T,1,
    M,F,T,0,
    M,H,R,b,16,
    M,H,R,v,0,0,0,0,
    '''
    buf = pack('>3sB', b'MAQ', 0)
    append(buf)
    buf = pack('>6sB', b'MSYOUT', 1)
    append(buf)
    buf = pack('>3sB', b'MFT', 0)
    append(buf)
    buf = pack('>3sBB', b'MHR', ord('b'), 10)
    append(buf)
    buf = pack('>3sBi', b'MHR', ord('v'), 0)
    append(buf)


def get_memory_data(dev):
    # each bit indicate one channel on/off
    chl_status = get_channel_status_bits()
    req = pack('>5sB8s1s', b':SGDM', chl_status, bytes([0]) * 8, b'#')
    print(req)

    dev.write(req)
    recv = dev.read(11)
    print(recv)

    # 4 args
    complete_flag, trig_status_flag, chl_status, chl_datalen = unpack('>BBBi', recv[4:])

    # compute all left data
    chl_count = bin(chl_status).count('1')
    left_len = chl_datalen * chl_count
    print(chl_datalen, chl_count)

    if not left_len or not complete_flag:
        return

    waveform_head_len = 1 + 4 * 6
    head_patten = '>B' + 'i' * 6

    wfs = []

    for chl in range(CHANNEL_NUMBER):
        chl_len = chl_datalen
        print(chl, chl_len)
        if chl > 0:
            dev.read(11)

        wf_data = b''

        i = 0
        while chl_len:
            if chl_len > MEM_BUFFER_SIZE:
                read_len = MEM_BUFFER_SIZE
            else:
                read_len = chl_len
            recv = dev.read(read_len)
            print(len(recv), ':', len(wf_data), ':', i)
            wf_data = wf_data + recv
            chl_len = chl_len - len(recv)
            i = i + 1

        print()
        wfi = WaveFormMemInfo(*unpack(head_patten, wf_data[:waveform_head_len]))
        wf_data = wf_data[waveform_head_len:wfi.data_len]
        # use data between start and screenlen
        wf = WaveFormMem(wfi, wf_data)
        print(wfi)
        wfs.append(wf)
    return wfs


def get_channel_status_bits():
    if CHANNEL_NUMBER == 2:
        return 0b0011
    else:
        return 0b1111


def get_screen_data(dev):
    # each bit indicate one channel on/off
    chl_status = get_channel_status_bits()
    req = pack('>5sB8s1s', b':SGDT', chl_status, bytes([0]) * 8, b'#')
    print(req)

    dev.write(req)
    recv = dev.read(16)
    print(recv)

    # 4 args
    args = recv[4:4 + 4]
    complete_flag, trig_status_flag, frame_count, chl_status = args
    chl_frame_len = unpack('>i', recv[8:8 + 4])[0]
    print(args, chl_frame_len, frame_count)

    # compute all left data
    chl_count = bin(chl_status).count('1')
    left_len = frame_count * chl_count * chl_frame_len
    print(left_len)

    if not left_len or not complete_flag:
        return

    left_waveforms = dev.read(left_len)
    waveform_head_len = 4 * 8
    head_patten = '>' + 'i' * 8

    wfs = [[] for _ in range(CHANNEL_NUMBER)]

    left = left_waveforms
    # parse channel by channel and frame by frame
    while len(left):
        wfi = WaveFormInfo(*unpack(head_patten, left[:waveform_head_len]))
        wf_data = left[waveform_head_len:wfi.len]
        # use data between start and screenlen
        wf = WaveForm(wfi, wf_data[wfi.start:wfi.start + wfi.screenlen])
        # print(wfi)
        wfs[wfi.name].append(wf)
        left = left[wfi.len:]

    return wfs


def get_all_info(dev):
    dev.write(b':SGAL#\n')
    recv = dev.read(6)
    print(recv)

    later_len = unpack('>i', recv[2:])[0]

    later_info = dev.read(later_len)
    print(later_info)
    # later will show how to parse all info


def get_send_cmds_m(cmds):
    """

    supposed there are two commands like 'CMD1', 'CMD02', then it will be sent like follow:
    ':M\x00\x00\x00\tCMD1CMD02'
    binary content is:
    58 77 0 0 0 9 67 77 68 49 67 77 68 48 50

    cmds = [b'CMD1', b'CMD02']
    arr = get_send_cmd_m(cmds)
    print(arr)
    for i in arr:
        print(i, end=' ')

    """
    cmds_len = reduce(lambda a, b: len(a) + len(b), cmds)
    return b':M' + pack('>i', cmds_len) + reduce(lambda a, b: a + b, cmds)


def for_run(dev_src):
    time.sleep(0.5)
    dev_src.write(b':SDSLRUN#')

    time.sleep(0.2)
    print('get_screen_data')
    return get_screen_data(dev_src)


def for_mem(dev_src):
    print('stop')
    time.sleep(0.2)
    dev_src.write(b':SDSLSTP#')
    print(dev_src.read(1024))

    time.sleep(0.2)
    print('get_memory_data')
    wfs = get_memory_data(dev_src)
    dev_src.write(b':SDSLRUN#')
    return wfs


def plot_screen(datas):
    for data in datas:
        y = np.array([int(v) for v in data])
        wf_data_len = len(y)
        x = np.linspace(0, wf_data_len, wf_data_len)
        # print(len(wf), type(x), type(y))
        plt.plot(x, y)

    plt.show()


def main():
    u_dev = next(usb_find_device())
    # print(u_dev)
    dev_src = USBSource(u_dev)

    # dev_src.write(b':SDSLVER#')
    # print(dev_src.read(1024))

    print('sync_cmds')
    sync_cmds = collect_cmds()
    dev_src.write(sync_cmds)

    wfs = for_run(dev_src)
    plot_screen([wf[-1].data for wf in wfs])

    # wfs = for_mem(dev_src)
    # plot_screen([wf.data for wf in wfs])

    dev_src.close()


if __name__ == '__main__':
    main()
