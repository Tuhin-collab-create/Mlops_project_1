import sys
import logging

def error_message_details(error: Exception, error_details: sys):
    """
    Extract the error line number and file details.
    """
    _, _, exc_tb = error_details.exc_info()

    file_name = exc_tb.tb_frame.f_code.co_filename
    line_number = exc_tb.tb_lineno

    error_message = (
        f"Error occurred in python script: "
        f"[{file_name}] at line number [{line_number}]: {str(error)}"
    )

    logging.error(error_message)
    return error_message


class MyException(Exception):
    def __init__(self, errormessage: str, errordetails: sys):
        super().__init__(errormessage)
        self.errormessage = error_message_details(errormessage, errordetails)

    def __str__(self):
        return self.errormessage
        
 