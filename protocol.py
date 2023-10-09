def protocol_header(room_name_size, operation, state, room_name, user_name, password) -> bytes:
    room_name = ljust_replace_space(room_name, room_name.encode("utf-8"), 8)
    user_name = ljust_replace_space(user_name, user_name.encode("utf-8"), 10)
    password = ljust_replace_space(password, password.encode("utf-8"), 11)

    return room_name_size.to_bytes(1, "big") + \
        operation.to_bytes(1, "big") + \
        state.to_bytes(1, "big") + \
        room_name.encode("utf-8") + \
        user_name.encode("utf-8") + \
        password.encode("utf-8")
        
def chatroom_protocol(room_name_size:int, operation:int, state:int, room_name:str, username: str, password:str):
    if len(room_name.encode("utf-8")) < 8:
        room_name = room_name.ljust(8, " ")
    
    if len(password.encode("utf-8")) < 10:
        password = password.ljust(10, " ")
        
    if len(password.encode("utf-8")) < 11:
        username = username.ljust(11, " ")
        
    return room_name_size.to_bytes(1, "big") + \
        operation.to_bytes(1, "big") + \
        state.to_bytes(1, "big") + \
        room_name.encode("utf-8") + \
        username.encode("utf-8") + \
        password.encode("utf-8")
        
def response_proctocol(room_name_size:int, operation:int, state:int, message: str):
    if len(message.encode("utf-8")) < 29:
        message = message.ljust(29, " ")
        
    return room_name_size.to_bytes(1, "big") + \
        operation.to_bytes(1, "big") + \
        state.to_bytes(1, "big") + \
        message.encode("utf-8")
        
def message_header(message) -> bytes:
    message = ljust_replace_space(message, message.encode("utf-8"), 32)
    return  bytes(message, "utf-8")

def ljust_replace_space(res: str,byte_str: bytes, num: int):
    return res.ljust(num, " ") if len(byte_str) < num else res

def get_room_name_size(header) -> int:
    return header[0]

def get_operation(header) -> int:
    return header[1]

def get_state(header) -> int:
    return header[2]

def get_room_name(header) -> str:
    return header[3:11].decode("utf-8").replace(" ","")

def get_user_name(header) -> str:
    return header[11:21].decode("utf-8").replace(" ","")

def get_password(header) -> str:
    return header[21:].decode("utf-8").replace(" ","")