import socket
import random
import string
import threading
import time

import protocol

class UserInfo:
    def __init__(self, udp_address, udp_port, userName, isHost=False) -> None:
        self.isHost = isHost
        self.udp_address = udp_address
        self.udp_port = udp_port
        self.userName = userName
        self.hadToken = False
        self.lastActiveTime = time.time()
    
class ChatRoomInfo:
    def __init__(self, roomMemberNum, roomName=None, roomPassword = None, accessToken=None,) -> None:
        self.maxroomMember = roomMemberNum
        self.roomName = roomName
        self.password = roomPassword
        self.udp_address = "0.0.0.0"
        self.udp_port = 9010
        self.accessToken = accessToken
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.buffer = 4096
        self.roomMember = []
        self.lastActiveTime = time.time()
        
    def addMember(self, address, userName, isHost):
        user = UserInfo(address[0], address[1], userName, isHost)
        self.roomMember.append(user)
    
    def leaveRoom(self, client_address):
        # IPアドレスで確認
        for i in range(len(self.roomMember)):
            if client_address[0] == self.roomMember[i].udp_address and client_address[1] == self.roomMember[i].udp_port:
                self.roomMember.pop(i)
                break
        print("New member", self.roomMember)
    
    def removeAllUser(self):
        pass
    
    # udpstart
    def udpstart(self):
        self.udp_socket.bind((self.udp_address, self.udp_port))
        print("UDP server start up on {} port: {}".format(self.udp_address, self.udp_port))
        self.udprecvAndSend()     
    
    def udprecvAndSend(self):
        try:
            while True:
                try:
                    data, client_address = self.udp_socket.recvfrom(self.buffer)
                    latest_messagedTime = time.time()
                    str_data = data.decode("utf-8")
                    if data == "exit":
                        self.leaveRoom(client_address)
                    
                    if latest_messagedTime - self.lastActiveTime > 600:
                        # 部屋を削除する。
                        self.roomMember.clear() 
                    self.lastActiveTime = latest_messagedTime
                    
                    print("Recived {} bytes from {}".format(len(data), client_address))
                    print(data)
                    [userName, messagedata] = str_data.split(":")
                    self.roomMember.append(client_address)
                    
                    if data:
                        print(self.roomMember)
                        for c_address in self.roomMember:
                            sent = self.udp_socket.sendto(data, c_address)      
                            print('Sent {} bytes back to {}'.format(sent, c_address))
                
                except KeyboardInterrupt:
                    print("\n KeyBoardInterrupted!")
                    break
        finally:
            self.udpclose()
    
    def udpclose(self):
        print("Closing server")
        self.udp_socket.close()
        
    def checkActive(self):
        pass
    


class Server:
    def __init__(self, tcp_address:str, tcp_port:int, udp_address:int, udp_port:int, buffer:int=4096) -> None:
        self.__tcpsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__tcpaddress = tcp_address
        self.__tcpport = tcp_port
        self.__udpaddress = udp_address
        self.__udp_prot = udp_port
        self.__buffer = buffer
        self.__roomList = {
            # roomName: ChatRoomInfo()
            "roomEx": ChatRoomInfo(4, "roomEx", "password"),
            "room2": ChatRoomInfo(4, "room2", "password"),
            }
        
    def generateToken(selef, size = 10):
        return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(size))        

    # TCP start
    def tcp_connetcion_start(self):
        self.__tcpsocket.bind((self.__tcpaddress, self.__tcpport))
        print("Starting up on {} port {}".format(self.__tcpaddress, self.__tcpport))
        self.__tcpsocket.listen(10)
        
        while True:
            try:
                tcp_connection, client_address = self.__tcpsocket.accept()
                threading.Thread(target=self.start_chat_of_TCP, args=(tcp_connection, client_address, )).start()
            except Exception as e:
                print("Socket close, Error => ", e)
                self.__tcpsocket.close()
            
    def start_chat_of_TCP(self, tcp_connection, client_address):
        print("Connection from {}".format(client_address))
        # 初回のクライアントからの送信
        # 状態等を送信
        message = "start"
        print("just started ")
        room_name_size, operation, state, room_name, password = self.tcp_server_recive(tcp_connection)
        print(room_name_size, operation, state, room_name, password)
        
        message = "Server start"
        # header (32バイト)：RoomNameSize（1バイト） | Operation（1バイト） | State（1バイト） | OperationPayloadSize（29バイト）
        # firstResponse = self.chatroom_protocol(room_name_size, operation, state, room_name, message)
        # self.tcp_response(tcp_connection, firstResponse)
        
        # サーバー初期化(0)
        # room作成
        if operation == 1:
            # リクエスト応答(1)
            state = 1
            message = "TrytoMakeRoom"
            res_make_init = self.chatroom_protocol(room_name_size, operation, state, room_name, message)
            self.tcp_response(tcp_connection, res_make_init)
            
            # リクエスト完了(2) : ルーム作成完了
            state = 2
            print("roomの作成を行います。作成するroomname  = {}".format(room_name))
            print("tcp_connection client 情報 {}".format(client_address))
            if not self.findRoom(room_name):
                print("その部屋名はありませんでした。部屋の作成 + 入室を行います。")
                message = "madeRoom"
                self.makeRoom(room_name_size,room_name, password, client_address, "morio")
                print("部屋の作成と入室を行いました。")
            else:
                print("その部屋名はすでに存在しています。")
                message = "Room Already Exists"
                # もう一度部屋名を入力してもらう。
            token = self.generateToken()
            res_made_room = self.chatroom_protocol(room_name_size, operation, state, room_name, message)
            self.tcp_response(tcp_connection,  res_made_room)
            
        # room参加
        elif operation == 2:
            print("join the room")
            message = "want to join the room"
            room_name_size, operation, state, room_name, password = self.tcp_server_recive(tcp_connection)
            print("部屋名、参加したいパスワードを受け取りました。", room_name, password)
            print(self.findRoom(room_name))
            if not self.findRoom(room_name):
                print("その部屋名は存在しません")
                # 部屋名をもう一度入力してもらう。
                message = "Room Does not Exist"
            else:
                print("部屋に入室します。")
                joinRoomCheck, message = self.check_joinRoom(room_name, password)
                print(joinRoomCheck, message)
                if joinRoomCheck:
                    self.joinRoom(room_name_size, room_name, client_address ,"kato")
                    
        else:
            message = "failed"
            res_failed =  self.chatroom_protocol(room_name_size, operation, state, room_name, message)
            self.tcp_response(tcp_connection, res_failed)
        
            
    def makeRoom(self, maxRoomNum, roomName, password, address, userName):
        message = "failed"
        token = self.generateToken()
        self.__roomList[roomName] = ChatRoomInfo(maxRoomNum, roomName, password, token)
        Host = UserInfo(address[0], address[1], userName, True)
        self.__roomList[roomName].roomMember.append(Host)
        message  = "MadeAndJoinedRoom"

    
    def check_joinRoom(self, roomName, password):
        message = "failed"
        join_room_flag = True
        
        # 部屋の許容人数に達している。
        if len(self.__roomList[roomName].roomMember) >= self.__roomList[roomName].maxroomMember:
            print("部屋は満室です。入室できません。他の部屋を選んでください。")
            message = "failed_roomsize_over"
            join_room_flag = False
            
        # パスワードが違う
        if self.__roomList[roomName].password != password:
            print("password : ",self.__roomList[roomName].password, "passwordInputed ", password)
            print("パスワードが間違っています。")
            message = "failed_wrong_password"
            # もう一度入力してもらう。
            join_room_flag = False
        message = "success"               
        return (join_room_flag, message)
    
    def joinRoom(self, maxRoomNum, roomName, address, userName):
        print("Roomに入室します。")
        user = UserInfo(address[0], address[1], userName, False)
        self.__roomList[roomName].roomMember.append(user)
        print("Roomに入室しました。")       
        print("RoomName: ", roomName, "部屋の最大人数: ", maxRoomNum, "現在の部屋の人数: ", len(self.__roomList[roomName].roomMember) )
           
            
    def findRoom(self, roomName):
        for room_n in self.__roomList:
            if room_n == roomName: return True
        return False
        
    def chatroom_protocol(self, room_name_size:int, operation:int, state:int, room_name:str, password:str):
        if len(room_name.encode("utf-8")) < 8:
            room_name = room_name.ljust(8, " ")
        
        if len(password.encode("utf-8")) < 21:
            password = password.ljust(21, " ")

        return room_name_size.to_bytes(1, "big") + \
            operation.to_bytes(1, "big") + \
            state.to_bytes(1, "big") + \
            room_name.encode("utf-8") + \
            password.encode("utf-8")
    
    def tcp_server_recive(self, tcp_connection):
        """
            サーバの初期化(0)
            Header(32): RoomNameSize(1) | Operation(1) | State(1) | room_name() | password()
        """
        data = tcp_connection.recv(32)
        print(data)
        room_name_size =int.from_bytes(data[:1], "big")
        operation = int.from_bytes(data[1:2], "big")
        state = int.from_bytes(data[2:3], "big")
        room_name = data[3:11].decode("utf-8").replace(" ","")
        password = data[11:].decode("utf-8").replace(" ","")
        
        return (room_name_size, operation, state, room_name, password)
    
    
    def tcp_response(self, tcp_connection, data):
        tcp_connection.sendall(data)
       
            
    def tcp_close(self, tcp_connection):
        print("Closing current tcp_connection")
        tcp_connection.close()
    

def main():    
    tcpaddress = '0.0.0.0'
    tcpport = 9001
    udpaddress = "0.0.0.0"
    udpport = 9010
    server = Server(tcpaddress, tcpport, udpaddress, udpport)
    
    server.tcp_connetcion_start()

    
if __name__ == "__main__":
    main()