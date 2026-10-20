import SocketTCP
address = ('192.168.100.120',8000)
# CLIENT
client_socketTCP = SocketTCP.SocketTCP()
client_socketTCP.connect(address)
# test 1
message = "Mensje de len=16".encode()
client_socketTCP.send(message,"go_back_n")
# test 2
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message,"go_back_n")
# test 3
message = "Mensaje de largo 19".encode()
client_socketTCP.send(message,"go_back_n")