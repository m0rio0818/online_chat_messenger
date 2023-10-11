import socket
import sys
import time
import threading
import getpass
import json

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
        self.__tcp_address = "localhost"
        self.__udp_address = "0.0.0.0"
        self.__tcp_port = 9001
        self.__udp_port = 9010
        
        self.__buffer = buffer
        self.__username = ""
        self.__room_name_size = ""
        self.__room_name = ""
        self.__token = ""
        self.__tokensize = ""
        self.__payloadSize = ""
        self.__password = ""
        self.__connection = True
        self.__lastSenttime = time.time()
        
        self.__udpsocket.bind((self.__udp_address, 0))
        
        
    
    def tcp_chatroom_protocolheader(self, room_name_size, opeartion, state, json_string_payload_size):
        return room_name_size.to_bytes(1, "big") + opeartion.to_bytes(1, "big") + state.to_bytes(1, "big") + json_string_payload_size.to_bytes(29, "big")
    
    def chang_to_json(self, data):
        return json.dumps(data)
    
    def startClient(self):
        self.tcp_start()
        threading.Thread(target=self.udp_sendMessage, daemon=True).start()
        self.udp_recive()
    
    # UDP start
    def udp_start(self):
        print("Starting up on UDP : {}  {}".format(self.__udpsocket, 0))
        # print(self.__udp_address, self.__udp_port)
        # thread_send = threading.Thread(target=self.udp_sendMessage)
        # thread_recive = threading.Thread(target = self.udp_recive)
        # thread_checkConnectiontime = threading.Thread(target=self.udp_checkTime)

        try:
            while self.__connection:
                self.udp_sendMessage()
                self.udp_recive()
                # thread_checkConnectiontime.start()
                # thread_send.start()
                # thread_recive.start()
                # thread_send.join()
                # thread_checkConnectiontime.join()
                # thread_recive.join()
                
        except KeyboardInterrupt as e:
            print("keyboardInterrrupt called!" + str(e))
            
        except OSError as e:
            print("OS Error ! " + str(e))
            
        finally:
            self.udp_close()    
        
    def udp_sendMessage(self):
        while self.__connection:
            try:
                message = input("Input message your messsage : ")
                if message == "exit":
                    break
                
                if not message:
                    print("No message please input again\n")
                    continue
                
                bMessage = bytes(self.__room_name + " : " + message, "utf-8")
                
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
        finally:
            self.udp_close()

    
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
            # threading.Thread(target=self.send()).start()
            self.tcp_Request()
        
    def connect(self):
        try:
            self.__tcpsocket.connect((self.__tcp_address, self.__tcp_port))
        except socket.error as e:
            print("ソケットエラー", e)
            sys.exit(1)
            
    def tcp_Request(self):
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
            
        noRoom = True
        
        
        # 部屋の許容人数の設定も行う。
        try:
            while noRoom:
                roomName = input("input Room Name you want to join in : ")
                password = input("input Password : ")
                self.__room_name = roomName
                self.__password = password
                self.__room_name_size = len(self.__room_name)
                self.__username = "Morio"          
                
                payload = {
                    # "roomName": self.__room_name,
                    "password": self.__password,
                    "userName" : self.__username
                }
                
                jsonPayload = self.chang_to_json(payload)
                self.__payloadSize = len(jsonPayload)
                print(jsonPayload)    
                
                if operation == 1:
                    # TCP接続確立後のヘッダー送信
                    # ヘッダー（32バイト）：RoomNameSize（1バイト） | Operation（1バイト） | State（1バイト） | OperationPayloadSize（29バイト)
                    header = self.tcp_chatroom_protocolheader(self.__room_name_size, operation, state, self.__payloadSize)
                    print(header)
                    self.__tcpsocket.send(header)
                    
                    # body : roomName (RoomNameSizeバイト) | operationPayload (OperationPayloadSizeバイト)
                    body = bytes(self.__room_name, "utf-8") + bytes(jsonPayload, "utf-8")
                    self.__tcpsocket.send(body)
                                        
                    # 1回目
                    response1 = self.__tcpsocket.recv(32)
                    room_name_size, operation, state, message1 = protocol.get_server_response_of_header(response1)
                    print(message1)
                    if state == 1:
                        print("リクエストの応答(1): サーバーから応答がありました。")
                        
                    # 2回目
                    response2 = self.__tcpsocket.recv(32)
                    room_name_size, operation, state, message2 = protocol.get_server_response_of_header(response2)
                    print(message2)
                    if state == 2:
                        # roomName = input("input room name where you want to join : ")
                        header = self.tcp_chatroom_protocolheader(self.__room_name_size, operation, state, self.__payloadSize)
                        self.__tcpsocket.send(header)
                        print("send!!")
                        print("リクエストの応答(2): 部屋が作成されました")
                    
                    # 3回目
                    response3 = self.__tcpsocket.recv(32)
                    room_name_size, operation, state, message3 = protocol.get_server_response_of_header(response3)
                    print("response3: ", room_name_size, operation, state, message3)
                    if message3 == "Made_And_Joined_Room":                    
                        # 4回目
                        self.__token = self.__tcpsocket.recv(128).decode("utf-8")
                        noRoom = False
                        self.__room_name  = roomName
                    # それ以外だと、もう一度名前を入力してもらいたい。
                    else:
                        pass
                        
                elif operation == 2:
                    # TCP接続確立後のヘッダー送信
                    header = protocol.chatroom_protocol(5, operation, state, "", "", "")
                    self.__tcpsocket.send(header)
                    
                    # 1回目
                    response_init = self.__tcpsocket.recv(32)
                    room_name_size, operation, state, message_init = protocol.get_server_response_of_header(response_init)
                    print(message_init)
                    
                    
                    join_roomName_password = protocol.chatroom_protocol(5, operation, state, roomName, self.__username, password)
                    self.__tcpsocket.send(join_roomName_password)
                    
                    # 2回目
                    response = self.__tcpsocket.recv(32)
                    room_name_size, operation, state, message = protocol.get_server_response_of_header(response)
                    if message == "Room_Does_not_Exist":
                        print("その部屋は存在しません。")
                    elif message == "Wrong_Password":
                        print("パスワードが間違っています。")
                    elif message == "Room_is_Full":
                        print("部屋は満室です。他の部屋を入力してください。")
                    else:
                        print("部屋に入室が完了いたしました。")
                        self.__token = self.__tcpsocket.recv(128).decode("utf-8")
                        noRoom = False
                        self.__room_name = roomName
                        print("token ",self.__token)
                        break
    
            self.tcp_close()
            threading.Thread(target=self.udp_start).start()
            
        except TimeoutError:
            print("Socket timeout, ending listning for serever messages")
            
    
    
    def tcp_close(self):
        print("Closing TCP socket...")
        self.__tcpsocket.close()
            
    
    
            
            
def main():
    tcplient = Client()
    tcplient.startClient()
    
if __name__ == "__main__":
    main()