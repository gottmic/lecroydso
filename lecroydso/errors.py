

class DSOConnectionError(Exception):
    """DSO Connection Error indicates an issue with connection
    """
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return 'DSOConnectionError, {0} '.format(self.message)
        else:
            return 'DSOConnectionError Exception'

class DSOIOError(Exception):
    """DSO IO Error indicates an issue with connection
    """
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return 'DSOIOError, {0} '.format(self.message)
        else:
            return 'DSOIOError Exception'

class ParametersError(Exception):
    """ParametersError indicates an error with supplied parameters"""
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return 'ParametersError, {0} '.format(self.message)
        else:
            return 'ParametersError Exception'