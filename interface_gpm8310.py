import pyvisa
import time
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class GPM8310:
    def __init__(self, ip_address='192.168.0.100', port='23'):
        self.rm = pyvisa.ResourceManager('@py')
        self.instrument_resource = f'TCPIP0::{ip_address}::{port}::SOCKET'
        logging.info(f"Connecting to instrument: {self.instrument_resource}")

        try:
            self.inst = self.rm.open_resource(self.instrument_resource)
            self.inst.read_termination = '\r\n'
            self.inst.write_termination = '\r\n'
            self.inst.timeout = 5000  # Timeout in milliseconds

            #clear the instrument
            self.inst.write('*CLS')

            #set the instruments to remote mode
            self.inst.write(':COMM:REM ON')

            #turn off verbose mode for shorter responses
            self.inst.write(':COMM:VERB OFF')

            #rset Numeric Normal to default
            self.inst.write(':NUM:NORM:PRESET')

            #set Numeric Normal Item 1 to Positive Watt-Hour (WHP)
            self.inst.write(':NUM:NORM:ITEM1 WHP')

            #set the number of numeric items to 1
            self.inst.write(':NUM:NORM:NUM 1')

            #set integration function to WATT
            self.inst.write(':INTEG:FUNC WATT')

            #set integration mode to NORMAL
            self.inst.write(':INTEG:MODE NORM')

            logging.info("Instrument initialized.")
        except Exception as e:
            logging.error(f"Failed to connect or initialize the instrument: {e}")
            self.inst = None
            self.rm.close()

    def start_integration(self):
        if self.inst is not None:
            try:
                self.inst.write(':INTEG:START')
                logging.info("Integration started.")
            except Exception as e:
                logging.error(f"Error starting integration: {e}")
        else:
            logging.warning("Instrument is not connected.")

    def stop_integration(self):
        if self.inst is not None:
            try:
                self.inst.write(':INTEG:STOP')
                logging.info("Integration stopped.")
            except Exception as e:
                logging.error(f"Error stopping integration: {e}")
        else:
            logging.warning("Instrument is not connected.")

    def reset_integration(self):
        if self.inst is not None:
            try:
                self.inst.write(':INTEG:RESET')
                logging.info("Integration reset.")
            except Exception as e:
                logging.error(f"Error resetting integration: {e}")
        else:
            logging.warning("Instrument is not connected.")

    def get_mwh_value(self):
        if self.inst is not None:
            try:
                response = self.inst.query(':NUM:NORM:VALUE?').strip()
                logging.debug(f"Raw response: '{response}'")

                match = re.search(r'([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', response)
                if match:
                    wh_value = float(match.group(1))
                    mwh_value = wh_value * 1000  # Convert Wh to mWh
                    logging.info(f"Parsed mWh value: {mwh_value}")
                    return mwh_value
                else:
                    logging.error(f"No numeric value found in response: '{response}'")
                    return None
            except Exception as e:
                logging.error(f"Error retrieving mWh value: {e}")
                return None
        else:
            logging.warning("Instrument is not connected.")
            return None

    def close(self):
        if self.inst is not None:
            try:
                self.inst.write(':COMM:REM OFF')
                self.inst.close()
                logging.info("Instrument connection closed.")
            except Exception as e:
                logging.error(f"Error closing instrument connection: {e}")
            finally:
                self.rm.close()
                logging.info("VISA resource manager closed.")
        else:
            logging.warning("Instrument is not connected.")


