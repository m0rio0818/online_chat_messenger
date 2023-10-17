     
def get_server_response_of_header(data):
    state = int.from_bytes(data[:1], "big")
    messagelength = int.from_bytes(data[2:], "big")     
    return (state, messagelength)
        
def tcp_chatroom_protocolheader( room_name_size, opeartion, state, json_string_payload_size):
        return room_name_size.to_bytes(1, "big") + opeartion.to_bytes(1, "big") + state.to_bytes(1, "big") + json_string_payload_size.to_bytes(29, "big")
    
def udp_protocolheader(room_name_size, tokenSize):
    return  room_name_size.to_bytes(1, "big") + tokenSize.to_bytes(1, "big")
        
def tcp_header_recive(tcp_connection):
    """
        サーバの初期化(0)
                    最大部屋収容人数  操作(1:作成, 2:入室)
        Header(32): RoomNameSize(1) | Operation(1) | State(1) | payloadSize(29)
    """
    data = tcp_connection.recv(32)
    room_name_size =int.from_bytes(data[:1], "big")
    operation = int.from_bytes(data[1:2], "big")
    state = int.from_bytes(data[2:3], "big")
    payloadSize = int.from_bytes(data[3:], "big")
    
    return (room_name_size, operation, state, payloadSize)
    
        
def get_udp_body(body):
    room_name_size = int.from_bytes(body[:1], "big")
    token_size = int.from_bytes(body[1:2], "big")
    room_name = body[2:room_name_size+2].decode()
    token = body[room_name_size+2:room_name_size+token_size+2].decode()
    message = body[room_name_size+token_size+2:].decode()
    return (room_name_size, token_size, room_name, token, message)

def tcp_body_recive(tcp_connection, room_name_size, payloadSize):
    data = tcp_connection.recv(room_name_size + payloadSize).decode()
    room_name = data[:room_name_size]
    payload = data[room_name_size: room_name_size+ payloadSize]
    return (room_name, payload)


def response_header( state, length_message):
    return state.to_bytes(1, "big") + length_message.to_bytes(31, "big")