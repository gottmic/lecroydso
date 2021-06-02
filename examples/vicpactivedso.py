from lecroydso.errors import DSOConnectionError, DSOIOError
from lecroydso  import ActiveDSO, LeCroyDSO
connection_string = 'VXI11:127.0.0.1'

def vicpactivedso():
    try:
        print('Trying to make a connection to ', connection_string)
        dso = LeCroyDSO(ActiveDSO(connection_string))
        print(dso.query('*IDN?'))

        dso.set_default_state()

        # send VBS style command
        dso.write_vbs('app.Acquisition.C1.VerScale=0.01')

        # query the value 
        response = dso.query('C1:VDIV?')
        print(response)

        # query it VBS style
        vbs_response = dso.query_vbs('app.Acquisition.C1.VerScale')
        print(vbs_response)

    except DSOConnectionError as e:
        print('ERROR: Unable to make a connection to ', connection_string)
        print(e.message)
        exit(-1)
    
    except DSOIOError:
        print('ERROR: Failed to communicate to the instrument')
        exit(-1)


if __name__ == '__main__':
    vicpactivedso()