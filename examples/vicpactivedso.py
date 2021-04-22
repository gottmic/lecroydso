from lecroydso.activedso import ActiveDSO
from lecroydso.errors import DSOConnectionError, DSOIOError
import os
from lecroydso  import ActiveDSO
from lecroydso import LeCroyDSO
connection_string = 'VXI11:127.0.0.1'

def vicpactivedso():
    try:
        print('Trying to make a connection to ', connection_string)
        connection = ActiveDSO(connection_string)
        dso = LeCroyDSO(connection)
        print(dso.send_query('*IDN?'))

        dso.set_default_state()

        # send VBS style command
        dso.send_vbs_command('app.Acquisition.C1.VerScale=0.01')

        # query the value 
        response = dso.send_query('C1:VDIV?')
        print(response)


    except DSOConnectionError:
        print('ERROR: Unable to make a connection to ', connection_string)
        exit(-1)
    
    except DSOIOError:
        print('ERROR: Failed to communicate to the instrument')
        exit(-1)

    finally:
        dso.disconnect_from_dso()
        dso.disconnect()

if __name__ == '__main__':
    vicpactivedso()