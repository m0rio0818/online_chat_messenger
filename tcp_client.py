import socket
import sys
import time
import threading
import getpass

import protocol

class UDPClient:
    def __init__(self, username, port, address="0.0.0.0", buffer=4096) -> None:
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__serverAddress = '0.0.0.0'
        self.__serverPort = 9010
        self.__username = username
        self.__address = address
        self.__port = int(port)
        self.__buffer = buffer
        self.__lastSenttime = time.time()
        self.__connection = True

class Client:
    def __init__(self, buffer=4096) -> None:
        self.__tcpsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__tcp_address = "0.0.0.0"
        self.__udp_address = '0.0.0.0'
        self.__tcp_port = 9001
        self.__udp_port = 9010
        
        self.__buffer = buffer
        self.__username = ""
        self.__room_name_size = ""
        self.__room_name = ""
        self.__token = ""
        self.__password = ""
        self.__connection = True
        self.__lastSenttime = time.time()
    
    # UDP start
    def udp_start(self):
        print("Starting up on UDP : {}  {}".format(self.__udpsocket, self.__udp_port))
        # print(self.__udp_address, self.__udp_port)
        self.__udpsocket.bind((self.__udp_address, self.__udp_port))
        thread_send = threading.Thread(target=self.udp_send)
        thread_recive = threading.Thread(target = self.udp_recive)
        thread_checkConnectiontime = threading.Thread(target=self.udp_checkTime)

        try:
            while self.__connection:
                thread_checkConnectiontime.start()
                thread_send.start()
                thread_recive.start()
                thread_send.join()
                thread_checkConnectiontime.join()
                thread_recive.join()
                
        except KeyboardInterrupt as e:
            print("keyboardInterrrupt called!" + str(e))
            
        except OSError as e:
            print("OS Error ! " + str(e))
            
        finally:
            self.udp_close()    
        
    def udp_send(self):
        while self.__connection:
            try:
                message = input("Input message your messsage : ")
                if message == "exit":
                    break
                
                if not message:
                    print("No message please input again\n")
                    continue
                
                bMessage = bytes(self.__username + " : " + message, "utf-8")
                
                # サーバーへデータを送信
                sent = self.__udpsocket.sendto(bMessage,(self.__udp_address, self.__udp_port))
                print('send {} bytes'.format(sent))
                self.__lastSenttime = time.time()
            
            except KeyboardInterrupt as e:
                print("keyboardInterrrupt called!" + str(e))
                break
    
    def udp_recive(self):
        try:
            while self.__connection:
                print("Waiting to recive....")
                data, server = self.__udpsocket.recvfrom(self.__buffer)
                print("Recived {!r}".format(data))
            print("接続が切れました。")
        except KeyboardInterrupt as e:
            print("keyboard interuppted !!!", str(e))
        except OSError as e:
            print("OS Error ! " + str(e))

    
    def udp_checkTime(self):
        try:    
            while True:
                currenttime = time.time()
                if currenttime - self.__lastSenttime > 600:
                    self.__connection = False
                    break
                time.sleep(1)
        except TimeoutError as e:
            print("セッション有効期限が切れました。")
            print(e)
        finally:
            print("接続時間が切れました。")
            self.udp_close()
            
        
    def udp_close(self):
        print("Closing UDP socket")
        self.__udpsocket.close()    
    # UDP end
            
    # TCP start
    def tcp_start(self):
        print("Connecting to TCP Server:  {}".format(self.__tcp_address, self.__tcp_port))
        while True:
            self.connect()
            threading.Thread(target=self.send()).start()
            # self.send()
        
    def connect(self):
        try:
            self.__tcpsocket.connect((self.__tcp_address, self.__tcp_port))
        except socket.error as e:
            print("ソケットエラー", e)
            sys.exit(1)
            
    def send(self):
        operationFlag = True
        while operationFlag:
            operation = input("1: You want to make Room.\n2: You want to join ChatRoom\n")
            operation = int(operation)
            if operation ==1 or operation == 2:
                operationFlag = False
            else:
                print("Input Proper Num")
        state = ""
        
        if operation == 1:
            state = 0
        else:
            state = 9
            
        # 部屋の許容人数の設定も行う。
        try:
            while True:
                if operation == 1:
                    print("operation == 1")
                    # TCP接続確立後のヘッダー送信
                    # flagPass = True
                    # while flagPass:
                    #     password = getpass.getpass("input your password : ")
                    #     if password == getpass.getpass("input your password one more time : "):
                    #         flagPass = False
                    #         self.__password = password
                    #     else:
                    #         print("Wrong password. please set password one more time")
                            
                    # roomname = input("input room name you want to make : ")
                    # self.__room_name = roomname
                            
                    header = protocol.chatroom_protocol(5, operation, state, "room1", "morio", "password")
                    self.__tcpsocket.send(header)
                    flagPass = True
                    
                    # 1回目
                    response1 = self.__tcpsocket.recv(32)
                    room_name_size, operation, state, message1 = protocol.get_server_response_of_header(response1)
                    print(room_name_size, operation, state, message1)
                    if state == 1:
                        print("リクエストの応答(1): サーバーから応答がありました。")
                        
                    # 2回目
                    response2 = self.__tcpsocket.recv(32)
                    room_name_size, operation, state, message2 = protocol.get_server_response_of_header(response2)
                    print(room_name_size, operation, state, message2)
                    if state == 2:
                        # roomName = input("input room name where you want to join : ")
                        header = protocol.chatroom_protocol(5, operation, state, "room1", "")
                        self.__tcpsocket.send(header)
                        print("send!!")
                        print("リクエストの応答(2): 部屋が作成されました")
                    
                    # 3回目
                    response3 = self.__tcpsocket.recv(32)
                    room_name_size, operation, state, message3 = protocol.get_server_response_of_header(response3)
                    print("response3: ", room_name_size, operation, state, message3)
                    if message3 == "Made_And_Joined_Room":                    
                        # 4回目
                        hostToken = self.__tcpsocket.recv(128)
                        print(hostToken)
                    # それ以外だと、もう一度名前を入力してもらいたい。
                    else:
                        break
                        
                elif operation == 2:
                    # TCP接続確立後のヘッダー送信
                    password = ""
                    header = protocol.chatroom_protocol(5, operation, state, "", "", "")
                    self.__tcpsocket.send(header)
                    
                    # 1回目
                    response_init = self.__tcpsocket.recv(32)
                    room_name_size, operation, state, message_init = protocol.get_server_response_of_header(response_init)
                    print(room_name_size, operation, state, message_init)
                    
                    roomName = input("input Room Name you want to join in : ")
                    password = input("input Password : ")
                    
                    join_roomName_password = protocol.chatroom_protocol(5, operation, state, roomName, "taro", password)
                    self.__tcpsocket.send(join_roomName_password)
                    
                    # 2回目
                    response = self.__tcpsocket.recv(32)
                    room_name_size, operation, state, message = protocol.get_server_response_of_header(response)
                    print(room_name_size, operation, state, message)
                    
                    break
                
            self.tcp_close()
            threading.Thread(target=self.udp_start())
            
        except TimeoutError:
            print("Socket timeout, ending listning for serever messages")
            
    
    
    def tcp_close(self):
        print("Closing TCP socket...")
        self.__tcpsocket.close()
            
    
    
            
            
def main():
    tcplient = Client()
    tcplient.tcp_start()
    
if __name__ == "__main__":
    main()