#-----------------------------------------------------------------------------
# $Header: //SoftwareQA/Test/IR/Nightly_Automation/MergeStartXreplay/ActiveDSO.py#3 $
# Summary:		Implementation of ActiveDSO class
# Authors:		Ashok Bruno
# Started:		2/8/2021
# Copyright 2021-2024 Teledyne LeCroy Corporation. All Rights Reserved.
#-----------------------------------------------------------------------------
#


maxLen = 1e6

#Interface
class DSOConnection:
    """DSOConnection is an abstract base class. All connections should implement these 
    """
    @property
    def errorString(self):
        pass

    @property
    def errorFlag(self):
        pass

    @property 
    def timeout(self):
        pass

    def reconnect(self):
        pass
            
    def send_command(self, message:str, terminator:bool=True):
        pass

    def read_string(self, max_bytes:int) -> str:
        pass

    def send_query(self, message:str, query_delay:float=None) -> str:
        pass

    def send_vbs_command(self, message:str):
        pass

    def send_vbs_query(self, message:str, query_delay:float=None) -> str:
        pass

    def wait_for_opc(self) -> bool:
        pass

    def write_raw(self, message:bytes, terminator:bool=True) -> bool:
        pass

    def read_raw(self, max_bytes:int) -> bytes:
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
