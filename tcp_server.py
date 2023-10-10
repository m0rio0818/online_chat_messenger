import socket
import random
import string
import threading
import time

import protocol

STATUS_MESSAGE = {
    000: "Failed",
    101: "Try_to_Make_Room",
    201: "Room_is_Full",
    301: "Joined_Room",
    401: "Made_And_Joined_Room",
    403: "Wrong_Password",
    404: "Room_Does_not_Exist",
    501: "Room_Already_Exists",
}


class UserInfo:
    def __init__(self, address, userName, isHost=False) -> None:
        self.isHost = isHost
        self.address = address[0]
        self.port = address[1]
        self.userName = userName
    
class ChatRoomInfo:
    def __init__(self, roomMemberNum, roomName=None, roomPassword = None, ) -> None:
        self.roomName = roomName
        self.maxroomMember = roomMemberNum
        self.password = roomPassword
        self.lastActiveTime = time.time()
        self.roomMember = []
        self.verified_token_to_address = {} # token : address
        
    def joinRoom(self, user:UserInfo, token: string, address: string):
        self.roomMember.append(user)
        self.verified_token_to_address[token] = address
    
    def checkLimitNumMember(self):
        print(len(self.roomMember), self.maxroomMember,)
        return len(self.roomMember) < self.maxroomMember
    
    def checkPassword(self, password):
        return self.password == password
    
    def leaveRoom(self,):
        pass
    
    def checkHost(self):
        for member in self.roomMember:
            if member.isHost: return True
        return False
    
    def removeAllUser(self):
        pass
        
    def checkActive(self):
        pass
    


class Server:
    def __init__(self, tcp_address:str, tcp_port:int, __udp_address:int, __udp__prot:int, buffer:int=4096) -> None:
        self.__tcpsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
        
        self.__tcpsocket.bind((self.__tcpaddress, self.__tcpport))
        self.__udpsocket.bind((self.__udp_address, self.__udp__prot))


        
    def generateToken(selef, size = 128):
        return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(size))      

    # udp_start
    def udp_start(self):
        print("UDP server start up on {} port: {}".format(self.__udp_address, self.__udp__prot))
        self.udp_recvAndSend()
    
    def udp_recvAndSend(self):
        try:
            while True:
                try:
                    data, client_address = self.__udpsocket.recvfrom(self.__buffer)
                    str_data = data.decode("utf-8")
                   
                    
                    print("Recived {} bytes from {}".format(len(data), client_address))
                    print(data)
                    [userName, messagedata] = str_data.split(":")
                    self.__roomMember.append(client_address)
                    
                    if data:
                        print(self.roomMember)
                        for c_address in self.roomMember:
                            sent = self.__udpsocket.sendto(data, c_address)      
                            print('Sent {} bytes back to {}'.format(sent, c_address))
                
                except KeyboardInterrupt:
                    print("\n KeyBoardInterrupted!")
                    break
        finally:
            self.udp_close()
    
    def udp_close(self):
        print("Closing UDP server")
        self.__udpsocket.close()  

    # TCP start
    def tcp_connetcion_start(self):
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
        # 初回のクライアントからの送信をを受信 + 確認内容送信
        message = "start"
        print("just started ")
        
        room_name_size, operation, state, room_name, username, password = self.tcp_server_recive(tcp_connection)
        
        message = "Server_start"
        # header (32バイト)：RoomNameSize（1バイト） | Operation（1バイト） | State（1バイト） | message（29バイト）
        # 1回目
        firstResponse = protocol.response_proctocol(room_name_size, operation, state, message)
        self.tcp_response(tcp_connection, firstResponse)
        
        # token クライアント生成
        token = self.generateToken()  
        client = UserInfo(client_address, username)
        
        # サーバー初期化(0)
        # room作成
        if operation == 1:
            # リクエスト応答(1)
            state = 1
            # 2回目
            res_make_init = protocol.response_proctocol(room_name_size, operation, state, STATUS_MESSAGE[101])
            self.tcp_response(tcp_connection, res_make_init)
            
            # リクエスト完了(2) : ルーム作成完了
            state = 2
            print("roomの作成を行います。作成するroomname  = {}".format(room_name))
            print("tcp_connection client 情報 {}:  ".format(client_address))
            
            # 部屋名が存在するか確認
            if not self.findRoom(room_name):
                # room 作成    
                self.makeRoom(room_name_size, room_name, password)
                # room参加
                self.__roomList[room_name].joinRoom(client, token, client_address)
                
                # 3回目
                res_made_room = protocol.response_proctocol(room_name_size, operation, state, STATUS_MESSAGE[404])
                self.tcp_response(tcp_connection,  res_made_room)
                # 4回目(Token)
                self.tcp_response(tcp_connection, bytes(token, "utf-8"))
            else:
                print("その部屋名はすでに存在しています。違う部屋名を再度選んでください。")
                # もう一度部屋名を入力してもらう。
                res_room_exist = protocol.response_proctocol(room_name_size, operation, state, STATUS_MESSAGE[501])
                self.tcp_response(tcp_connection, res_room_exist)
            
        # room参加
        elif operation == 2:
            print("join the room")
            message = "want_to_join_the_room"
            room_name_size, operation, state, room_name, username, password = self.tcp_server_recive(tcp_connection)
            print("部屋名、参加したいパスワードを受け取りました。", username, room_name, password)

            # 部屋が見つからなかった場合
            if not self.findRoom(room_name):
                print("その部屋名は存在しません")
                message = "Room_Does_not_Exist"
                # 2回目
                res_not_exist = protocol.response_proctocol(room_name_size, operation, state, STATUS_MESSAGE[404])
                self.tcp_response(tcp_connection, res_not_exist)    
                print("データを送信しました。")
            # 部屋が見つかった場合
            else:
                print("部屋に入室します")
                joinRoomCheck, num = self.check_joinRoom(room_name, password)
                print(joinRoomCheck, num)
                if joinRoomCheck:
                    self.__roomList[room_name].joinRoom(client, client_address, token)
                    print("部屋に入室しました。")
                # 2回目
                res_joined_room = protocol.response_proctocol(room_name_size, operation, state, STATUS_MESSAGE[num])
                self.tcp_response(tcp_connection, res_joined_room)
            
        else:
            res_failed =  protocol.response_proctocol(room_name_size, operation, state, STATUS_MESSAGE[000])
            self.tcp_response(tcp_connection, res_failed)
        
        self.tcp_close(tcp_connection)
        
    def tcp_response(self, tcp_connection, data):
        tcp_connection.sendall(data)
            
    def tcp_close(self, tcp_connection):
        print("Closing current TCP connection")
        tcp_connection.close()
            
            
            
    def makeRoom(self, maxRoomNum, roomName, password):
        print("その部屋名はありませんでした。部屋の作成 + 入室を行います。")        
        self.__roomList[roomName] = ChatRoomInfo(maxRoomNum, roomName, password)
        print("部屋の作成と入室を行いました。")
    
    def check_joinRoom(self, roomName, password):
        if not self.__roomList[roomName].checkPassword(password):
            return (False, 403)
        if not self.__roomList[roomName].checkLimitNumMember():
            return (False, 201)
        return (True, 301)
        
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
    
    
    

def main():    
    tcpaddress = '0.0.0.0'
    tcpport = 9001
    udpaddress = "0.0.0.0"
    udpport = 9010
    server = Server(tcpaddress, tcpport, udpaddress, udpport)
    
    server.tcp_connetcion_start()

    
if __name__ == "__main__":
    main()