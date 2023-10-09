import socket
import random
import string
import threading
import time

import protocol

class UserInfo:
    def __init__(self, __udp_address, __udp__prot, userName, isHost=False) -> None:
        self.isHost = isHost
        self.__udp_address = __udp_address
        self.__udp__prot = __udp__prot
        self.userName = userName
        self.hadToken = False
        self.lastActiveTime = time.time()
    
class ChatRoomInfo:
    def __init__(self, roomMemberNum, roomName=None, roomPassword = None, accessToken=None,) -> None:
        self.maxroomMember = roomMemberNum
        self.roomName = roomName
        self.password = roomPassword
        self.__udp_address = "0.0.0.0"
        self.__udp__prot = 9010
        self.accessToken = accessToken
        self.buffer = 4096
        self.roomMember = []
        self.lastActiveTime = time.time()
        
    def addMember(self, user:UserInfo):
        # user = UserInfo(address[0], address[1], userName, isHost)
        self.roomMember.append(user)
    
    def leaveRoom(self, client_address):
        # IPアドレスで確認
        for i in range(len(self.roomMember)):
            if client_address[0] == self.roomMember[i].__udp_address and client_address[1] == self.roomMember[i].__udp__prot:
                self.roomMember.pop(i)
                break
        print("New member", self.roomMember)
    
    def removeAllUser(self):
        pass
        
    def checkActive(self):
        pass
    


class Server:
    def __init__(self, tcp_address:str, tcp_port:int, __udp_address:int, __udp__prot:int, buffer:int=4096) -> None:
        self.__tcpsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__tcpaddress = tcp_address
        self.__tcpport = tcp_port
        self.__udp_address = __udp_address
        self.__udp__prot = __udp__prot
        self.__buffer = buffer
        self.__roomList = {
                # roomName: ChatRoomInfo()
                "roomEx": ChatRoomInfo(4, "roomEx", "password"),
                "room2":  ChatRoomInfo(4, "room2", "password"),
            }

    # udp_start
    def udp_start(self):
        self._udpsocket.bind((self.__udp_address, self.__udp__prot))
        print("UDP server start up on {} port: {}".format(self.__udp_address, self.__udp__prot))
        self.udp_recvAndSend()
    
    def udp_recvAndSend(self):
        try:
            while True:
                try:
                    data, client_address = self._udpsocket.recvfrom(self.__buffer)
                    str_data = data.decode("utf-8")
                   
                    
                    print("Recived {} bytes from {}".format(len(data), client_address))
                    print(data)
                    [userName, messagedata] = str_data.split(":")
                    self.roomMember.append(client_address)
                    
                    if data:
                        print(self.roomMember)
                        for c_address in self.roomMember:
                            sent = self._udpsocket.sendto(data, c_address)      
                            print('Sent {} bytes back to {}'.format(sent, c_address))
                
                except KeyboardInterrupt:
                    print("\n KeyBoardInterrupted!")
                    break
        finally:
            self.udp_close()
    
    def udp_close(self):
        print("Closing UDP server")
        self._udpsocket.close()
        
    def generateToken(selef, size = 128):
        return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(size))        

    # TCP start
    def tcp_connetcion_start(self):
        self.__tcpsocket.bind((self.__tcpaddress, self.__tcpport))
        print("Starting up on {} port {}".format(self.__tcpaddress, self.__tcpport))
        self.__tcpsocket.listen(10)
        
        while True:
            try:
                tcp_connection, client_address = self.__tcpsocket.accept()
                threading.Thread(target=self.start_chat_of_TCP, args=(tcp_connection, client_address,)).start()
                
                
            except Exception as e:
                print("Socket close, Error => ", e)
                self.__tcpsocket.close()
            
    def start_chat_of_TCP(self, tcp_connection, client_address):
        print("Connection from {}".format(client_address))
        # 初回のクライアントからの送信をを受信 + 確認し再送信
        # 状態等を送信
        message = "start"
        print("just started ")
        
        room_name_size, operation, state, room_name, username, password = self.tcp_server_recive(tcp_connection)
        print(room_name_size, operation, state, room_name, username, password)
        
        message = "Server_start"
        # header (32バイト)：RoomNameSize（1バイト） | Operation（1バイト） | State（1バイト） | message（29バイト）
        # 1回目
        firstResponse = protocol.response_proctocol(room_name_size, operation, state, message)
        self.tcp_response(tcp_connection, firstResponse)
        
        # サーバー初期化(0)
        # room作成
        if operation == 1:
            # リクエスト応答(1)
            state = 1
            message = "Try_to_Make_Room"
            # 2回目
            res_make_init = protocol.response_proctocol(room_name_size, operation, state, message)
            self.tcp_response(tcp_connection, res_make_init)
            
            # リクエスト完了(2) : ルーム作成完了
            state = 2
            print("roomの作成を行います。作成するroomname  = {}".format(room_name))
            print("tcp_connection client 情報 {}".format(client_address))
            
            if not self.findRoom(room_name):
                print("その部屋名はありませんでした。部屋の作成 + 入室を行います。")
                message, token = self.makeRoom(room_name_size, room_name, password, client_address, username)
                print("部屋の作成と入室を行いました。")
                res_made_room = protocol.response_proctocol(room_name_size, operation, state, message)
                # 3回目
                self.tcp_response(tcp_connection,  res_made_room)
                # 4回目(Token)
                self.tcp_response(tcp_connection, bytes(token, "utf-8"))

            else:
                print("その部屋名はすでに存在しています。違う部屋名を再度選んでください。")
                message = "Room_Already_Exists"
                # もう一度部屋名を入力してもらう。
                res_room_exist = protocol.response_proctocol(room_name_size, operation, state, message)
                self.tcp_response(tcp_connection, res_room_exist)
            
            
        # room参加
        elif operation == 2:
            print("join the room")
            message = "want_to_join_the_room"
            room_name_size, operation, state, room_name, username, password = self.tcp_server_recive(tcp_connection)
            print("部屋名、参加したいパスワードを受け取りました。", username, room_name, password)
            print(self.findRoom(room_name))
            
            # 部屋名が見つからなかった場合
            if not self.findRoom(room_name):
                print("その部屋名は存在しません")
                # 部屋名をもう一度入力してもらう。
                message = "Room_Does_not_Exist"
                # 2回目
                res_not_exist = protocol.response_proctocol(room_name_size, operation, state, message)
                self.tcp_response(tcp_connection, res_not_exist)    
                print("データを送信しました。")
            # 部屋名が見つかった場合
            else:
                print("部屋に入室します")
                joinRoomCheck, message = self.check_joinRoom(room_name, password)
                if joinRoomCheck:
                    self.joinRoom(room_name_size, room_name, client_address, username)
                # 2回目
                res_joined_room = protocol.response_proctocol(room_name_size, operation, state, message)
                self.tcp_response(tcp_connection, res_joined_room)    
            
        else:
            message = "failed"
            res_failed =  protocol.response_proctocol(room_name_size, operation, state, message)
            self.tcp_response(tcp_connection, res_failed)
        
        self.tcp_close(tcp_connection)
        
            
    def makeRoom(self, maxRoomNum, roomName, password, address, userName):
        message = "failed"
        token = self.generateToken()
        self.__roomList[roomName] = ChatRoomInfo(maxRoomNum, roomName, password, token)
        
        Host = UserInfo(address[0], address[1], userName, True)
        self.__roomList[roomName].roomMember.append(Host)
        print(self.__roomList)
        message  = "Made_And_Joined_Room"
        return (message, token)

    
    def check_joinRoom(self, roomName, password):
        message = "success"
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
        return (join_room_flag, message)
    
    def joinRoom(self, maxRoomNum, roomName, address, userName):
        user = UserInfo(address[0], address[1], userName, False)
        self.__roomList[roomName].addMember(user)
        print("Roomに入室しました。")       
        print("RoomName: ", roomName, "部屋の最大人数: ", maxRoomNum, "現在の部屋の人数: ", len(self.__roomList[roomName].roomMember) )
           
            
    def findRoom(self, roomName):
        for room_n in self.__roomList:
            if room_n == roomName: return True
        return False
    
    def tcp_server_recive(self, tcp_connection):
        """
            サーバの初期化(0)
            Header(32): RoomNameSize(1) | Operation(1) | State(1) | room_name(10) |  userName(10)  | password(10)
        """
        data = tcp_connection.recv(32)
        room_name_size =int.from_bytes(data[:1], "big")
        operation = int.from_bytes(data[1:2], "big")
        state = int.from_bytes(data[2:3], "big")
        room_name = data[3:11].decode("utf-8").replace(" ","")
        username = data[11:21].decode("utf-8").replace(" ", "")
        password = data[21:].decode("utf-8").replace(" ","")
        
        return (room_name_size, operation, state, room_name, username, password)
    
    
    def tcp_response(self, tcp_connection, data):
        tcp_connection.sendall(data)
       
            
    def tcp_close(self, tcp_connection):
        print("Closing current TCP connection")
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