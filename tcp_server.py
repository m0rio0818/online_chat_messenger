import socket
import random
import string
import threading
import time
import json

import protocol

STATUS_MESSAGE = {
    000: "Failed",
    100: "Server start",
    101: "Try to Make Room",
    201: "Room is Full",
    301: "Joined Room",
    401: "Made And Joined Room",
    403: "Wrong Password",
    404: "Room Does not Exist",
    501: "Room Already Exists",
    505: "you left the room. please re enter the room if u want to join this community"
}


class UserInfo:
    def __init__(self, token, address, port, userName, isHost=False) -> None:
        self.token = token
        self.isHost = isHost
        self.address = address
        self.port = port
        self.userName = userName
        self.lastActiveTime = time.time()
    
class ChatRoomInfo:
    def __init__(self, roomMemberNum, roomName=None, roomPassword=None,) -> None:
        self.roomName = roomName
        self.maxroomMember = roomMemberNum
        self.password = roomPassword
        self.lastActiveTime = time.time()
        self.roomMember = []
        self.verified_token_to_address = {} # token : address
        
    def joinRoom(self, user:UserInfo, address: string, token: string,):
        self.roomMember.append(user)
        self.verified_token_to_address[token] = address
        print("現在の部屋人数: ", len(self.roomMember), "最大部屋人数: " ,self.maxroomMember,)
    
    def sendMessagetoAllUser(self, udpsocket, message):
        for tokenkey in self.verified_token_to_address.keys():
            if type(message) == "number":
                udpsocket.sendto(protocol.protocol_header(444), self.verified_token_to_address[tokenkey])
            else:
                udpsocket.sendto(bytes(message, "utf-8"), self.verified_token_to_address[tokenkey])

    def checkLimitNumMember(self):
        return len(self.roomMember) < self.maxroomMember
    
    def checkPassword(self, password):
        print(self.password, password)
        return self.password == password
    
    def leaveRoom(self, token, udpsocket,):
        print("現在の部屋のメンバー", self.roomMember)
        for i in range(len(self.roomMember)):
            if self.roomMember[i].token == token:
                if self.roomMember[i].isHost:
                    self.sendMessagetoAllUser(udpsocket, 404)
                    self.roomMember.clear()
                    self.verified_token_to_address.clear()
                    print("現在の部屋のメンバー", self.roomMember)
                    print("全員部屋を退出しました。")
                    break
                else:
                    udpsocket.sendto(protocol.protocol_header(444), self.verified_token_to_address[token])   
                    self.roomMember.pop(i)
                    self.verified_token_to_address.pop(token)
                    print("現在の部屋のメンバー", self.roomMember)
                    print("部屋を退出しました。")
                    break

        
    def changeClientAddress(self, token, address):
        for member in self.roomMember:
            if member.token == token:
                member.address = address[0]
                member.port = address[1]
                return

    def findRoomMember(self, token):
        for member in self.roomMember:
            if member.token == token:
                return member
        return False
    
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
                "roomEx": ChatRoomInfo(4, "roomEx", "password"),
                "room2":  ChatRoomInfo(4, "room2", "password"),
            }
            # roomName: ChatRoomInfo()
        self.__tcpsocket.bind((self.__tcpaddress, self.__tcpport))
        self.__udpsocket.bind((self.__udp_address, self.__udp__prot))


    def generateToken(selef, size = 128):
        return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(size))      
    
    # udp_start      
    def udp_recvAndSend(self):
        try:
            while True:
                try:
                    body, client_address = self.__udpsocket.recvfrom(self.__buffer)
                    room_name, token, message = protocol.get_udp_body(body)
        
                    if (self.__roomList[room_name].verified_token_to_address[token] != client_address):
                        # tokenによって、addressをTCPの時から上書きする。
                        self.__roomList[room_name].verified_token_to_address[token] =  client_address
                        self.__roomList[room_name].changeClientAddress(token, client_address)
                    
                    print("Recived {} [{} bytes] from {}".format(message, len(body), client_address))
                    # ここでユーザーの最新アクティブ時間の変更
                    self.__roomList[room_name].findRoomMember(token).lastActiveTime = time.time()
                    
                    if message == "exit":
                        self.__roomList[room_name].leaveRoom(token, self.__udpsocket)
            
                        
                    if message:
                        self.__roomList[room_name].sendMessagetoAllUser(self.__udpsocket, message)
                        self.__roomList[room_name].changeClientAddress(token, client_address)
                
                except KeyboardInterrupt:
                    print("\n KeyBoardInterrupted!")
                    break
                except Exception as e:
                    print("例外発生: ", e)
                
        finally:
            self.udp_close()
    
    def udp_close(self):
        print("Closing UDP server")
        self.__udpsocket.close()  

    def startServer(self):
        # TCP 並列処理
        threading.Thread(target=self.wait_tcp_connetcion, daemon=True).start()
        self.udp_recvAndSend()
        
    # TCP start
    def wait_tcp_connetcion(self):
        print("Starting up on {} TCP port {}".format(self.__tcpaddress, self.__tcpport))
        self.__tcpsocket.listen(10)
        
        while True:
            try:
                tcp_connection, client_address = self.__tcpsocket.accept()
                threading.Thread(target=self.start_room_TCP, args=(tcp_connection, client_address,)).start()
                
            except Exception as e:
                print("Socket close, Error => ", e)
                self.__tcpsocket.close()
            
    def start_room_TCP(self, tcp_connection, client_address):
        roomCheck = True
        while roomCheck:
            print("TCP just started ")
            print("TCP Connection from {}".format(client_address))
                        
            # header受信
            room_name_size, operation, state, payloadSize = protocol.tcp_header_recive(tcp_connection)
            # body受信        
            room_name, opeartionPayloadjson = protocol.tcp_body_recive(tcp_connection, room_name_size, payloadSize)
            opeartionPayload = json.loads(opeartionPayloadjson)

            # header (32バイト)：RoomNameSize（1バイト） | Operation（1バイト） | State（1バイト） | message（29バイト）
            # サーバー初期化(0)
            print("Server just start!")
            # token クライアント生成
            token = self.generateToken()
            client = UserInfo(token, opeartionPayload["ip"], opeartionPayload["port"], opeartionPayload["userName"],  True if operation == 1 else False)
            
            # room作成
            if operation == 1:
                state = 1
                # リクエスト応答(1)
                # response_header(32バイト)： state(1バイト) | statusMessageLength(31バイト)
                firstResponse_header = protocol.response_header(state, len(STATUS_MESSAGE[101]))
                self.tcp_response(tcp_connection, firstResponse_header)
                # response_body: statusMessage(statusMessageLenバイト)
                self.tcp_response(tcp_connection, bytes(STATUS_MESSAGE[101], "utf-8"))
                
                print("roomの存在チェックを行います。roomName : {}".format(room_name))
                print("tcp_connection client 情報 {}: ".format(client_address))
                
                state = 2
                # 部屋名が存在するか確認
                if not self.findRoom(room_name):
                    print("その部屋を作成 + 参加します")
                    # room 作成    
                    # リクエスト完了(2) : ルーム作成完了
                    self.makeRoom(room_name, opeartionPayload["password"])
                    self.__roomList[room_name].joinRoom(client, client_address, token,)
                    
                    # 2回目
                    res_make_init = protocol.response_header(state, len(STATUS_MESSAGE[401]))
                    self.tcp_response(tcp_connection, res_make_init)
                    self.tcp_response(tcp_connection, bytes(STATUS_MESSAGE[401], "utf-8"))
                    # 3回目(Token)
                    self.tcp_response(tcp_connection, bytes(token, "utf-8"))
                    roomCheck = False
                    
                else:
                    print("その部屋名はすでに存在しています。違う部屋名を再度入力してください。")
                    state = 9
                    res_room_exist = protocol.response_header(state, len(STATUS_MESSAGE[501]))
                    self.tcp_response(tcp_connection, res_room_exist)
                    self.tcp_response(tcp_connection, bytes(STATUS_MESSAGE[501], "utf-8"))
                    
            # room参加
            elif operation == 2:
                print("try to join the room")
                print("部屋名、参加したいパスワードを受け取りました。", opeartionPayload["userName"], room_name, opeartionPayload["password"])

                # 部屋が見つからなかった場合
                if not self.findRoom(room_name):
                    print("その部屋名は存在しません")
                    # 1回目
                    firstResponse_header = protocol.response_header(state, len(STATUS_MESSAGE[404]))
                    self.tcp_response(tcp_connection, firstResponse_header)
                    self.tcp_response(tcp_connection, bytes(STATUS_MESSAGE[404], "utf-8"))

                # 部屋が見つかった場合
                else:
                    print("部屋に入室します")
                    joinRoomCheck, num = self.check_joinRoom(room_name, opeartionPayload["password"])
                    if joinRoomCheck:
                        self.__roomList[room_name].joinRoom(client, client_address, token)
                        # 1回目
                        secondeResponse_header = protocol.response_header(state,  len(STATUS_MESSAGE[num]))
                        self.tcp_response(tcp_connection, secondeResponse_header)
                        self.tcp_response(tcp_connection, bytes(STATUS_MESSAGE[num], "utf-8"))
                        # 2回目(token)
                        self.tcp_response(tcp_connection, bytes(token, "utf-8"))
                        print("部屋に入室しました。")
                    else:
                        print("エラーのため、部屋に入室できませんでした。", STATUS_MESSAGE[num])
                        # 2回目
                        secondeResponse_header = protocol.response_header(state,  len(STATUS_MESSAGE[num]))
                        self.tcp_response(tcp_connection, secondeResponse_header)
                        self.tcp_response(tcp_connection, bytes(STATUS_MESSAGE[num], "utf-8"))
                
            else:
                res_failed =  protocol.response_header(state, STATUS_MESSAGE[000])
                self.tcp_response(tcp_connection, res_failed)
                
        self.tcp_close(tcp_connection)
            
    def tcp_response(self, tcp_connection, data):
        tcp_connection.sendall(data)
            
    def tcp_close(self, tcp_connection):
        print("Closing current TCP connection")
        tcp_connection.close()
            
    def response_to_client(self, tcp_connection, state, num):
        secondeResponse_header = protocol.response_header(state,  len(STATUS_MESSAGE[num]))
        self.tcp_response(tcp_connection, secondeResponse_header)
        self.tcp_response(tcp_connection, bytes(STATUS_MESSAGE[num], "utf-8"))
            
    def makeRoom(self, roomName, password, maxRoomNum=4):
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
   
    

def main():    
    tcpaddress = '127.0.0.1'
    tcpport = 9001
    udpaddress = '127.0.0.1'
    udpport = 9010
    server = Server(tcpaddress, tcpport, udpaddress, udpport)
    server.startServer()

    
if __name__ == "__main__":
    main()