from socket import AF_INET, socket, SOCK_STREAM


def connect(address, cmd):
    client = socket(AF_INET, SOCK_STREAM)
    client.connect(address)
    client.settimeout(2)

    client.send(cmd)
    r = client.recv(1024)
    print(r)


if __name__ == '__main__':
    adr = '192.168.1.60', 2000
    cmd = b':SDSLVER#'

    # adr = '192.168.1.72', 3000
    # cmd = b'*IDN?\n'
    # cmd = b'STARTBIN'
    connect(adr, cmd)
