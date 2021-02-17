import os
from lecroydso import ActiveDSO
from lecroydso import LeCroyDSO
connection_string = 'VXI11:127.0.0.1'

def vicpactivedso(self):
    self.my_conn = ActiveDSO(connection_string)     # replace with IP address of the scope
    if self.my_conn is None:
        print('ActiveDSO is not installed or registered')

    if not self.my_conn.connected:
        print('ActiveDSO unable to make a connection to {0}'.format(connection_string))

    self.my_conn.send_command('CHDR OFF')
    chdr = self.my_conn.send_query('CHDR?')
    if 'WARNING' in chdr:
        self.fail("Connection on the instrument set to TCPIP, please set to LXI")

if __name__ == '__main__':
    if os.name == 'nt':
        vicpactivedso()