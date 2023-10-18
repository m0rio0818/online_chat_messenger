import socket
import sys
import time
import threading
import getpass
import json

import protocol

STATUS_MESSAGE = {
    444: "you left the room. please re enter the room if u want to join this community"
}



class Client:
    def __init__(self, buffer=4096) -> None:
        self.__tcpsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__tcp_address = "0.0.0.0"
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
        self.__firstSent = False
        
        self.__udpsocket.bind((self.__udp_address, 0))
        
    def sendMessage(self, message):
        messageHeader = protocol.udp_protocolheader(self.__room_name_size, self.__tokensize)
        # サーバーへメッセージを送信
        bMessage = bytes(self.__room_name + self.__token + message, "utf-8")
        sent = self.__udpsocket.sendto(messageHeader + bMessage, (self.__udp_address, self.__udp_port))
        return sent
        
    def udp_sendMessage(self):
        try:
            while self.__connection:
                if not self.__firstSent:
                    message = ""
                    sent = self.sendMessage(message)
                    self.__firstSent = True
                
                message = input("Input message your messsage : ")
                if not message:
                    print("No message please input again\n")
                    continue
                
                               
                sent = self.sendMessage(message)
                print('send {} bytes'.format(sent))
                if message == "exit":
                    self.__connection = False
                
        except KeyboardInterrupt as e:
            sent = self.sendMessage("exit")
            print("keyboardInterrrupt called!" + str(e))

        finally:
            print("UDP Send を終了します。")
            self.udp_close() 
    
    def udp_recive(self):
        try:
            while self.__connection:
                print("Waiting to recive....")
                data, server = self.__udpsocket.recvfrom(self.__buffer)
                # print("受け取ったメッセージ", data.decode())
                # print(int.from_bytes(data, "big"))
                # if int.from_bytes(data, "big") == 444:
                #     print("この切断メッセージを受け取りました。")
                  
                print("Recived {}".format(data.decode()))
            print("接続が切れました。")
        except KeyboardInterrupt as e:
            print("keyboard interuppted !!!", str(e))
        except OSError as e:
            print("OS Error ! " + str(e))
        finally:
            self.udp_close()
                    
    def udp_close(self):
        print("Closing UDP socket")
        self.__udpsocket.close()    
    # UDP end
     
    
    # TCP start
    def start(self):
        print("Connecting to TCP Server:  {}".format(self.__tcp_address, self.__tcp_port))
        self.connect()
        self.tcp_Request()
        print("Connnecting UDP...")
        threading.Thread(target=self.udp_sendMessage, daemon=True).start()
        self.udp_recive()
        
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
            if operation == 1 or operation == 2:
                operationFlag = False
            else:
                print("Input Proper Num")
        state = ""
    
        if operation == 1:
            state = 0
        else:
            state = 9
            
        username = input("input your Name (userName) : ")
        self.__username = username      
            
        noRoom = True      
        try:
            while noRoom:
                roomName = input("input Room Name you want to join in : ")
                password = input("input Password : ")
                self.__room_name = roomName
                self.__password = password
                self.__room_name_size = len(self.__room_name)
            
                payload = {
                    "password": self.__password,
                    "userName" : self.__username,
                    "ip" : self.__tcp_address,
                    "port" : self.__tcp_port,
                }
               
                jsonPayload = json.dumps(payload)
                self.__payloadSize = len(jsonPayload)
                print(jsonPayload)
                
                # TCP接続確立後のヘッダー送信
                # ヘッダー（32バイト）：RoomNameSize（1バイト） | Operation（1バイト） | State（1バイト） | OperationPayloadSize（29バイト)
                header = protocol.tcp_chatroom_protocolheader(self.__room_name_size, operation, state, self.__payloadSize)
                self.__tcpsocket.send(header)
                
                # body : roomName (RoomNameSizeバイト) | operationPayload (OperationPayloadSizeバイト)
                body = bytes(self.__room_name, "utf-8") + bytes(jsonPayload, "utf-8")
                self.__tcpsocket.send(body)
                if operation == 1:
                    # 1回目
                    response1 = self.__tcpsocket.recv(32)
                    state, messagelength = protocol.get_server_response_of_header(response1)
                    firstresponse_Message = self.__tcpsocket.recv(messagelength).decode()
                    if state == 1:
                        print("リクエストの応答(1): サーバーから応答がありました。")
                        print(firstresponse_Message)
                        
                    # 2回目
                    response2 = self.__tcpsocket.recv(32)
                    state, messagelength = protocol.get_server_response_of_header(response2)
                    print(state, messagelength)
                    if state == 2:
                        print("リクエストの応答(2): 部屋が作成されました")
                        secondresponse_Message = self.__tcpsocket.recv(messagelength).decode()
                        print(secondresponse_Message)
                        self.__token = self.__tcpsocket.recv(128).decode("utf-8")
                        self.__tokensize = len(self.__token)
                        noRoom = False
                    else:
                        secondresponse_Message = self.__tcpsocket.recv(messagelength).decode()
                        print(secondresponse_Message)
                        noRoom = True
                        continue
                        
                elif operation == 2:
                    # 1回目
                    response_init = self.__tcpsocket.recv(32)
                    state, messagelength = protocol.get_server_response_of_header(response_init)
                    message = self.__tcpsocket.recv(messagelength).decode()
                    
                    if message == "Room Does not Exist":
                        print("その部屋は存在しません。")
                    elif message == "Wrong Password":
                        print("パスワードが間違っています。")
                    elif message == "Room is Full":
                        print("部屋は満室です。他の部屋を入力してください。")
                    else:
                        print("部屋に入室が完了いたしました。")
                        # 2回目　token取得
                        self.__token = self.__tcpsocket.recv(128).decode("utf-8")
                        self.__tokensize = len(self.__token)
                        noRoom = False
                        break
    
            self.tcp_close()
            threading.Thread(target=self.udp_recive, daemon=True).start()
            # threading.Thread(target=self.udp_sendMessage, daemon=True).start()
            self.udp_sendMessage()
            
        except TimeoutError:
            print("Socket timeout, ending listning for serever messages")
            
        except KeyboardInterrupt as e:
            print("keyBoard Interrupt. plz retry it.")
            

    def tcp_close(self):
        print("Closing TCP socket...")
        self.__tcpsocket.close()
    
            
def main():
    tcplient = Client()
    tcplient.start()
    
if __name__ == "__main__":
    main()