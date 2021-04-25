import socket
import select


def echo_server(address):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(10)
    reads = []
    reads.append(sock)
    while True:
        r, _, _ = select.select(reads, [], [], 10)
        for s in r:
            if s == sock:
                client, addr = sock.accept()
                reads.append(client)
            else:
                try:
                    data = s.recv(10000)
                    print("recv:", data)
                except socket.error:
                    print("close connetion:" + str(s.getpeername()))
                    reads.remove(s)


if __name__ == '__main__':
    echo_server(('', 3333))
