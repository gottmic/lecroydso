#-----------------------------------------------------------------------------
# Summary:		Implementation of ActiveDSO class
# Authors:		Ashok Bruno
# Started:		2/8/2021
# Copyright 2021-2024 Teledyne LeCroy Corporation. All Rights Reserved.
#-----------------------------------------------------------------------------
#


maxLen = 1e6

#Interface
class DSOConnection:
    @property
    def error_string(self):
        pass

    @property
    def error_flag(self):
        pass

    @property 
    def timeout(self):
        pass

    @property
    def query_response_max_length(self):
        pass

    @property
    def insert_wait_opc(self):
        pass

    def reconnect(self):
        pass
            
    def write(self, message:str, terminator:bool=True):
        pass

    def read(self, max_bytes:int) -> str:
        pass

    def query(self, message:str, query_delay:float=None) -> str:
        pass

    def write_vbs(self, message:str):
        pass

    def query_vbs(self, message:str, query_delay:float=None) -> str:
        pass

    def wait_opc(self) -> bool:
        pass

    def write_raw(self, message:bytes, terminator:bool=True) -> bool:
        pass

    def read_raw(self, max_bytes:int) -> memoryview:
        pass

    def disconnect(self):
        pass

    def get_panel(self) -> str:
        pass

    def set_panel(self, panel: str) -> bool:
        pass

    def transfer_file_to_dso(self, remote_device: str, remote_filename: str, local_filename: str) -> bool:
        pass

    def transfer_file_to_pc(self, remote_device: str, remote_filename: str, local_filename: str) -> bool:
        pass

    def store_hardcopy_to_file(self, format:str, auxFormat:str, filename:str):
        pass
