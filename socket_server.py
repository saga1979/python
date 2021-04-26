import sys
import socketserver
from codecs import decode
import socket
import select


def echo_server(address):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(10)
    reads = []
    reads.append(sock)
    client = None
    print("socket server started...")
    stop = False
    while True:
        r, _, _ = select.select(reads, [], [], 10)
        for s in r:
            if s == sock:
                if client is None:
                    client, addr = sock.accept()
                reads.append(client)
            else:
                try:

                    data = s.recv(10000)
                    if len(data) == 0:
                        s.close()
                        reads.remove(s)
                    else:
                        print("recv:", decode(data, 'utf-8'))
                except socket.error:
                    print("close connetion:" + str(s.getpeername()))
                    reads.remove(s)


if __name__ == '__main__':
    echo_server(('', 3333))


# class MyTCPHandler(socketserver.BaseRequestHandler):

#     def handle(self):
#         # self.request is the TCP socket connected to the client
#         self.data = self.request.recv(1024).strip()
#         print("{} wrote:".format(self.client_address[0]))
#         print(self.data)
#         # just send back the same data, but upper-cased
#         #self.request.sendall(self.data.upper())

# if __name__ == "__main__":
#     HOST, PORT = "localhost", 3333
#     with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
#         server.serve_forever()


# class MyUDPHandler(socketserver.BaseRequestHandler):
#     def handle(self):
#         data = self.request[0].strip()
#         socket = self.request[1]
#         print("{} wrote:".format(self.client_address[0]))
#         print(data)
#         socket.sendto(data.upper(), self.client_address)


# if __name__ == "__main__":
#     HOST, PORT = "localhost", 9999
#     with socketserver.UDPServer((HOST, PORT), MyUDPHandler) as server:
#         server.serve_forever()


# HOST, PORT = "localhost", 9999
# data = " ".join(sys.argv[1:])

# # SOCK_DGRAM is the socket type to use for UDP sockets
# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# # As you can see, there is no connect() call; UDP has no connections.
# # Instead, data is directly sent to the recipient via sendto().
# sock.sendto(bytes(data + "\n", "utf-8"), (HOST, PORT))
# received = str(sock.recv(1024), "utf-8")

# print("Sent:     {}".format(data))
# print("Received: {}".format(received))
