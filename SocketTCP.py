from socket_con_perdida import Sock
import random
import socket
from  slidingWindowCC import SlidingWindowCC
from socketUDP import SocketUDP
from CongestionControl import CongestionControl

SYN = 1
ACK = 2
FIN = 4
INIT = 8

TIMER = 1

class Segment:
    def __init__(self,head=0,sequence=0,body=b""):
        self.head: int = head
        self.sequence: int = sequence
        self.body: bytes = body
    def __bytes__(self):
        return self.head.to_bytes(1) + self.sequence.to_bytes(3) + self.body

class SocketTCP:
    
    congestion_controller = CongestionControl(8) 
    def __init__(self):
        self.socketUDP = SocketUDP()
        self.congestion_control_on = False
        self.socket_tcp = SocketUDP()
        self.sequence = 0
        self.buff_size = 16
        self.address = None

        self.init_message = None
        self.last_message = None

        self.length = 0

        self.closed = False

    def set_congestion_control(self,value:bool):
        self.congestion_control_on = value

    @staticmethod
    def parse_segment(segment:bytes) -> Segment:
        if len(segment) > 4:
            body = segment[4:]
        else:
            body = b""
        print(segment[0])
        return Segment(segment[0],int.from_bytes(segment[1:4]),body)
    
    @staticmethod
    def create_segment(data:Segment) -> bytes:
        return bytes(data)

    def bind(self,address = ("",0)):
        self.socketUDP.bind(address)

    def connect(self,address):

        self.sequence = random.randint(0,100)

        data = Segment(SYN,self.sequence)
        resp = None
        while True:
            self.socketUDP.sendto(self.create_segment(data),address)
            try:
                accept, self.address = self.socketUDP.recvfrom(4+self.buff_size)
                resp = self.parse_segment(accept)
                if resp.head == SYN + ACK and resp.sequence >= self.sequence:
                    break
            except TimeoutError:
                continue
        

        self.sequence = resp.sequence + 1
        resp.sequence = self.sequence

        resp.head = ACK

        self.socketUDP.sendto(self.create_segment(resp),self.address)
        print(f"Mi direccion {self.socketUDP.socket_udp.getsockname()}")
        print(f"Direccion de comunicacion {self.address}")

    def accept(self):
        connect,address = self.socketUDP.recvfrom(4+self.buff_size)
        connect_parsed = self.parse_segment(connect)
        if connect_parsed.head != SYN:
            return
        new_sockect = SocketTCP()
        new_sockect.sequence = connect_parsed.sequence + 1
        connect_parsed.sequence = new_sockect.sequence
        connect_parsed.head = SYN + ACK
        new_sockect.address = address
        while True:
            new_sockect.socketUDP.sendto(self.create_segment(connect_parsed),new_sockect.address)
            try:
                last_ack, _ = new_sockect.socketUDP.recvfrom(4+self.buff_size)
                break
            except TimeoutError:
                continue
        last_ack_parsed = self.parse_segment(last_ack)

        if last_ack_parsed.head != ACK:
            new_sockect.init_message = last_ack_parsed

        print(f"Mi direccion {self.socketUDP.socket_udp.getsockname()}")
        print(f"Direccion de comunicacion {new_sockect.address}")
        return new_sockect,new_sockect.socketUDP.socket_udp.getsockname()

    def send_using_stop_and_wait(self,message:bytes) -> None:
        length = len(message)
        data = Segment(0,self.sequence,length.to_bytes(16))
        while len(message) > 0:
            print("Send: mandando info")
            self.socket_tcp.sendto(self.create_segment(data),self.address)
            try:
                self.socket_tcp.settimeout(TIMER)
                print("Send: Esperando confirmacion")
                response, _ = self.socket_tcp.recvfrom(4+self.buff_size)
                response_parsed = self.parse_segment(response)
                if response_parsed.head == ACK and response_parsed.sequence > self.sequence:
                    print("Send: Mensaje de confirmacion recivido")
                    data_used = int.from_bytes(response_parsed.body)

                    print(f"Send: bytes usados {data_used}")

                    message = message[data_used:]

                    self.sequence = response_parsed.sequence

                    data = Segment(0,self.sequence,message[:min(self.buff_size,len(message))])

                else:
                    print("Send: Confirmacion errornea")
                    continue
            except socket.timeout:
                print("Send: Timer excedido")
                continue

    def wrap_data_as_segment(self,data:bytes,seq:int):
        return self.create_segment(Segment(0,seq,data))

    def is_valid_ack_go_back_n(self,current_segment,answer):
        return self.parse_segment(current_segment) == self.parse_segment(answer)

    @staticmethod
    def divide_message(message,size):
        result = []
        while len(message) > 0:
            cut = min(len(message),size)
            result.append(message[:cut])
            message = message[cut:]
        return result

    def send_using_go_back_n(self,message:bytes):
        print("Entrando a send")
        init = False
        message_length = str(len(message)).encode()
        message_length_aux = len(message)
        # dividimos el mensaje en trozos de 16 bytes
        data_list = self.divide_message(message, self.congestion_controller.MSS)

        # usamos una ventana para que vean como se usa
        initial_seq = self.sequence
        data_to_send = SlidingWindowCC(self.congestion_controller.get_cwnd() if self.congestion_control_on else 8, [message_length] + data_list, initial_seq)
        wnd_index = 0

        # partimos armando y enviando el primer segmento
        current_segments = []
        for i in range(self.congestion_controller.get_cwnd() if self.congestion_control_on else 8):
            current_data = data_to_send.get_data(i)
            current_seq = data_to_send.get_sequence_number(i)
            if current_data != None:
                if not init:
                    print(current_data)
                    current_segment = self.create_segment(Segment(INIT,current_seq,message_length_aux.to_bytes(16)))
                    init = True
                    current_segments.append(current_segment)
                else:
                    current_segment = self.wrap_data_as_segment(current_data, current_seq)
                    current_segments.append(current_segment)

        while len(current_segments) > 0:
            for segment in current_segments:
                self.socketUDP.sendto(segment, self.address, timer_index=0)
            try:
                self.socketUDP.settimeout(TIMER)
                for segment in current_segments:
                    answer, address = self.socketUDP.recvfrom(self.buff_size)
                    if self.congestion_control_on:
                        if self.parse_segment(answer).sequence > data_to_send.get_sequence_number(self.congestion_controller.get_cwnd()-1) and self.congestion_control_on:
                            data_to_send.move_window(self.parse_segment(answer).sequence-data_to_send.get_sequence_number(self.congestion_controller.get_cwnd()-1))
                    if self.is_valid_ack_go_back_n(segment,answer):
                        if self.congestion_control_on:
                            self.congestion_controller.event_ack_received()
                            data_to_send.update_window_size(self.congestion_controller.get_cwnd())
                        #if self.parse_segment(segment).sequence == self.sequence:
                            print("MOviendo ventatna")
                    data_to_send.move_window(1)
                    self.sequence = data_to_send.get_sequence_number(0)
                self.socketUDP.stop_timer(timer_index=0) # solo hay un timer
                # actualizamos el segmento
                current_segments = []
                for i in range(self.congestion_controller.get_cwnd() if self.congestion_control_on else 8):
                    current_data = data_to_send.get_data(i)
                    current_seq = data_to_send.get_sequence_number(i)
                    if current_data is not None:
                        current_segment = self.wrap_data_as_segment(current_data, current_seq)
                        current_segments.append(current_segment)

            except TimeoutError:
                print("Time out")
                if self.congestion_control_on:
                    self.congestion_controller.event_timeout()
                    data_to_send.update_window_size(self.congestion_controller.get_cwnd())
                for i in range(self.congestion_controller.get_cwnd() if self.congestion_control_on else 8):
                    current_data = data_to_send.get_data(i)
                    current_seq = data_to_send.get_sequence_number(i)
                    if current_data is not None:
                        current_segment = self.wrap_data_as_segment(current_data, current_seq)
                        current_segments.append(current_segment)

    def send(self,message:bytes,mode="stop_and_wait") -> None:
        if mode == "stop_and_wait":
            self.send_using_stop_and_wait(message)
        elif mode == "go_back_n":
            self.send_using_go_back_n(message)

    def recv_using_stop_and_wait(self,buff_size:int):
        self.socket_tcp.settimeout(None)
        if self.closed:
            return b""

        total_message = b""
        message_parsed = None

        while self.length <= 0:
            if self.init_message != None:
                message_parsed = self.init_message
                self.init_message = None
            else:
                message,_ = self.socket_tcp.recvfrom(4+self.buff_size)
                message_parsed = self.parse_segment(message)

            if message_parsed.sequence < self.sequence:
                self.socket_tcp.sendto(self.last_message,self.address)
                continue

            if message_parsed.head == FIN:
                print("Recv: Cerrado")
                self.recv_close()
                return b""
            
            self.length = int.from_bytes(message_parsed.body)
            print(f"Recv: Seteando largo {self.length}")
            self.sequence += 16
            data = Segment(ACK,self.sequence,int(0).to_bytes(self.buff_size))
            self.last_message = self.create_segment(data)
            self.socket_tcp.sendto(self.last_message,self.address)
        while len(total_message) < min(buff_size,self.length):
            print("Solicitando informacion")
            message, _ = self.socket_tcp.recvfrom(4+self.buff_size)
            message_parsed = self.parse_segment(message)
            if message_parsed.sequence < self.sequence:
                print("Recv: Mensaje ya recibido")
                self.socket_tcp.sendto(self.last_message,self.address)
                continue
            cut = min(buff_size - len(total_message),self.buff_size)
            total_message += message_parsed.body[:cut]
            print(total_message.decode())
            self.sequence = message_parsed.sequence + cut
            data = Segment(ACK,self.sequence,cut.to_bytes(16))
            self.last_message = self.create_segment(data)
            self.socket_tcp.sendto(self.last_message,self.address)
        self.length -= buff_size
        return total_message

    def recv_using_go_back_n(self,buff_size:int):
        if self.closed:
            return b""

        total_message = b""
        message_parsed = None

        while self.length <= 0:
            if self.init_message != None:
                if message_parsed.head != INIT:
                    self.socketUDP.sendto(self.last_message,self.address)
                    self.init_message = None
                    continue
                message_parsed = self.init_message
                self.init_message = None
                self.sequence = message_parsed.sequence
            else:
                message,_ = self.socketUDP.recvfrom(4+self.buff_size)
                message_parsed = self.parse_segment(message)

                if message_parsed.head != INIT:
                    self.socketUDP.sendto(self.last_message,self.address)
                    continue

            if message_parsed.head == FIN:
                print("Recv: Cerrado")
                self.recv_close()
                return b""
            
            self.length = int.from_bytes(message_parsed.body)
            print(f"Recv: Seteando largo {self.length}")
            self.sequence = message_parsed.sequence
            data = Segment(ACK,self.sequence,int(0).to_bytes(self.buff_size))
            self.last_message = self.create_segment(data)
            self.socketUDP.sendto(self.last_message,self.address)
        while len(total_message) < min(buff_size,self.length):
            print("Solicitando informacion")
            message, _ = self.socketUDP.recvfrom(4+self.buff_size)
            message_parsed = self.parse_segment(message)
            if message_parsed.sequence < self.sequence:
                print("Recv: Mensaje ya recibido")
                self.socketUDP.sendto(self.last_message,self.address)
                continue
            if message_parsed.sequence > self.sequence + self.congestion_controller.MSS + 1:
                continue
            cut = min(buff_size - len(total_message),self.buff_size)
            total_message += message_parsed.body[:cut]
            print(total_message.decode())
            self.sequence = message_parsed.sequence
            data = Segment(ACK,self.sequence,cut.to_bytes(16))
            self.last_message = self.create_segment(data)
            self.socketUDP.sendto(self.last_message,self.address)
        self.length -= buff_size
        return total_message

    def recv(self,buff_size:int,mode="stop_and_wait") -> bytes:
        if mode == "stop_and_wait":
            return self.recv_using_stop_and_wait(buff_size)
        elif mode == "go_back_n":
            return self.recv_using_go_back_n(buff_size)
        

    def close(self):
        print("Entrando a close")
        end_message = Segment(FIN,self.sequence,b"")
        while True:
            self.socket_tcp.sendto(self.create_segment(end_message),self.address)
            try:
                self.socket_tcp.settimeout(TIMER)
                resp, _= self.socket_tcp.recvfrom(4+self.buff_size)
                if self.parse_segment(resp).head == FIN + ACK:
                    self.sequence = self.parse_segment(resp).sequence
                    break
                continue
            except socket.timeout:
                continue
        self.sequence += 1
        for i in range(3):
            last_ack = Segment(ACK,self.sequence,b"")
            self.socket_tcp.sendto(self.create_segment(last_ack),self.address)
            self.socket_tcp.settimeout(TIMER)
            try:
                self.socket_tcp.recvfrom(4+self.buff_size)
            except socket.timeout:
                continue
        self.closed = True

    def recv_close(self):
        print("Cerrando")
        close = False
        self.sequence += 1
        while not close:
            data = Segment(ACK+FIN,self.sequence,b"")
            self.socket_tcp.sendto(self.create_segment(data),self.address)
            for i in range(3):
                try:
                    self.socket_tcp.settimeout(TIMER)
                    resp, _ = self.socket_tcp.recvfrom(4+self.buff_size)
                    resp_parsed = self.parse_segment(resp)
                    if resp_parsed.head == FIN:
                        break
                    elif resp_parsed.head == ACK:
                        close = True
                        break
                except socket.timeout:
                    continue
        self.closed = True