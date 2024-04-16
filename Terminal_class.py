import time
import datetime

from class_p2p import P2P

CMD = {'Init': 0X00,
       'File_Info': 0X01,
       'Get_File': 0x02,
       'Get_Sample': 0x03,
       'Set_Time': 0x04,
       'Delete_File': 0x05,
       'Unblock_Scales': 0x06}

CMD_length = {'Init': 0,  # инициализирует обмен
              'File_Info': 0,  # инициализирует передачу информации о файлах
              'Get_File': 1,  # отправляет номер файла
              'Get_Sample': 1 + 2,  # отправляет номер файла и строку данных
              'Set_Time': 1 + 6,  # отправляет дату и время (Г,М,Д,ДН,Ч:М:С)
              'Delete_File': 1,
              'Unblock_Scales': 4}

RSP_length = {'Init': 1 + 1,  # получет количество файлов
              'File_Info': 1 + 2 + 4,  # получает название, кол-во записей, последний UNIX (*files_amount)
              'Get_File': 2 + 2 + 4,  # получает номер, вес и UNIX (*counter)
              'Get_Sample': 2 + 2 + 4,  # получает номер, вес и UNIX
              'Set_Time': 0,
              'Delete_File': 0,
              'Unblock_Scales': 1}  # получает подтверждение

# ard = P2P('COM13', 115200)
# ard.open_com_port()
# time.sleep(3)
# print('Ready')


# def Connect(port_name: str, baud_rate: int):
#     _ard = P2P(port_name, baud_rate)
#     _ard.open_com_port()
#     time.sleep(3)
#     print('Ready')
#     return _ard


class arduino(P2P):
    def Init(self):
        self.open_com_port()
        time.sleep(2)
        print('Ready')
        _block_status = 0
        _files_amount = 0
        self.send_request(CMD['Init'], bytearray())
        _cmd_error, _data = self.parse_responses(RSP_length['Init'], RSP_length['Init'])
        for response in _data:
            _files_amount = int.from_bytes(response[:1], 'little', signed=False)
            _block_status = int.from_bytes(response[1:], 'little', signed=False)
        time.sleep(0.5)
        _block_status = False if (_block_status == 0) else True
        return _cmd_error, _files_amount, _block_status

    def File_Info(self, files_amount: int):
        self.send_request(CMD['File_Info'], bytearray())
        _error_list, byte_list = self.parse_responses(RSP_length['File_Info'], files_amount)
        _messages = []
        print (byte_list)
        for response in byte_list:
            file = response[0]
            lines = int.from_bytes(response[1:3], 'little', signed=False)
            unix = int.from_bytes(response[3:7], 'little', signed=False)
            _message = {'file': file, 'lines': lines, 'unix': unix}
            print(_message)
            _messages.append(_message)
        print(_error_list)
        return _error_list, _messages

    def Get_File(self, file: int, lines: int):
        request = bytearray([file])
        self.send_request(CMD['Get_File'], request)
        _error_list, _byte_list = self.parse_responses(RSP_length['Get_File'], lines)

        _messages = []
        for response in _byte_list:
            count = int.from_bytes(response[:2], 'little', signed=False)
            data = int.from_bytes(response[2:4], 'little', signed=True)
            unix = int.from_bytes(response[4:8], 'little', signed=False)
            if (count == 0):
                medium_limit = data
                heavy_limit = unix
            else:
                id = 1 if (data < 0) else 0
                flag = 1 if abs(data) < medium_limit else (2 if abs(data) < heavy_limit else 3)
                message = {'ID': count + 1, 'WeighingId': id, 'Weight': abs(data), 'Flag': flag, 'SavedDateTime': unix}
                # print(message)
                _messages.append(message)

        a = list(range(2, lines + 1))
        counts = []
        for message in _messages:
            counts.append(message['ID'])
        lost = []
        for item in a:
            if item not in counts:
                lost.append(item)
        if len(lost):
            print(f"did't get: {lost}")
            print(f"did't get {len(lost)} messages, from {lines}")
        else:
            print("All files successfully received")
        # print(_messages)

        return _messages, lost

    def Get_Sample(self, file, sample):
        request = bytearray([file])
        request += sample.to_bytes(2, 'little', signed=False)
        self.send_request(CMD['Get_Sample'], request)
        _cmd_error, response = self.receive_response_while(RSP_length['Get_Sample'], 0.5 + sample / 1000)

        count = int.from_bytes(response[:2], 'little', signed=False)
        data = int.from_bytes(response[2:4], 'little', signed=True)
        unix = int.from_bytes(response[4:8], 'little', signed=False)
        id = 1 if (data < 0) else 0
        flag = 1 if abs(data) < 1180 else (2 if abs(data) < 1300 else 3)
        _message = {'ID': count + 1, 'WeighingId': id, 'Weight': abs(data), 'Flag': flag, 'SavedDateTime': unix}
        if unix == 0 and _cmd_error == 0:
            print("row exceeds the number of measurement")
            # _cmd_error = 1
        # print(_message)
        return _cmd_error, _message

    def Set_Time(self):
        _date = datetime.datetime.now()
        # print(_date)
        # print(_date.year)
        # print(_date.month)
        # print(_date.day)
        # print(_date.weekday)
        # print(_date.hour)
        # print(_date.minute)
        # print(_date.second)
        year = _date.year - 2000

        request = bytearray()
        request += year.to_bytes(1, 'little', signed=False)
        request += _date.month.to_bytes(1, 'little', signed=False)
        request += _date.day.to_bytes(1, 'little', signed=False)
        request += _date.weekday().to_bytes(1, 'little', signed=False)
        request += _date.hour.to_bytes(1, 'little', signed=False)
        request += _date.minute.to_bytes(1, 'little', signed=False)
        request += _date.second.to_bytes(1, 'little', signed=False)
        # print(request)

        self.send_request(CMD['Set_Time'], request)
        _cmd_error, data = self.receive_response(RSP_length['Set_Time'])

        return _cmd_error

    def Delete_File(self, file):
        request = bytearray([file])

        self.send_request(CMD['Delete_File'], request)
        _cmd_error, data = self.receive_response(RSP_length['Delete_File'])

        return _cmd_error
    
    def Unblock_Scales(self, pwd):
        request = bytearray()
        request += pwd.to_bytes(4, 'little', signed=True)

        self.send_request(CMD['Unblock_Scales'], request)
        _cmd_error, _data = self.parse_responses(RSP_length['Unblock_Scales'], RSP_length['Unblock_Scales'])

        for response in _data:
            unblock_status = int.from_bytes(response[:1], 'little', signed=False)
        unblock_status = False if (unblock_status == 0) else True

        return _cmd_error, unblock_status

# ard = arduino('COM13', 115200)

# print(ard.Init())


# cmd_error, files_amount = ard.Init()
# ard.open_com_port()
# print(files_amount)
# error_list, messages = ard.File_Info(files_amount)
# print(f"errors: {error_list}")

# ard.Get_File(1, 370)

# cmd_error, message = Get_Sample(2, 999)
# print(f"error: {cmd_error}, message: {message}")

# cmd_error = ard.Set_Time()
# print(cmd_error)

