import http.server
import socketserver
import threading
import time
import os
import logging
from GPM8310 import GPM8310

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def free_port(port):
    try:
        result = os.popen(f"lsof -i tcp:{port}").read()
        if result:
            logging.info(f"Port {port} is currently in use. Attempting to free it.")

            lines = result.strip().split('\n')
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    pid = int(parts[1])
                    os.system(f"kill -9 {pid}")
                    logging.info(f"Process {pid} on port {port} terminated.")
        else:
            logging.info(f"Port {port} is free.")
    except Exception as e:
        logging.error(f"Error freeing port {port}: {e}")

class RequestHandler(http.server.BaseHTTPRequestHandler):
    result_counter = 0
    #value sequence
    values = [768, 1024, 2048, 3078]

    def do_POST(self):
        logging.info(f"Received POST request from {self.client_address} to path {self.path}")
        logging.debug(f"Headers: {self.headers}")

        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8').strip()
        logging.info(f"Received data: '{post_data}'")

        if post_data == "START":
            logging.info("Processing START command.")
            try:
                # Start the energy measurement
                energy_meter.reset_integration()
                energy_meter.start_integration()
                logging.info("Energy measurement started.")
            except Exception as e:
                logging.error(f"Error starting energy measurement: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Failed to start energy measurement.")
                return
        elif post_data.startswith("END"):
            logging.info("Processing END command.")
            parts = post_data.split(",")
            if len(parts) == 2:
                try:
                    latency = float(parts[1])
                    logging.info(f"Latency received: {latency} seconds")
                    energy_meter.stop_integration()
                    logging.info("Energy measurement stopped.")
                    mwh_value = energy_meter.get_mwh_value()
                    if mwh_value is not None:
                        logging.info(f"Energy consumed: {mwh_value} mWh")
                        
                        #determine the current value based on the result_counter
                        index = (self.result_counter // 6) % len(self.values)
                        value = self.values[index]
                        self.result_counter += 1

                        #store or log the results
                        with open("results.csv", "a") as f:
                            f.write(f"{latency},{mwh_value},{value}\n")
                        logging.info("Results saved to 'results.csv'.")
                    else:
                        logging.error("Failed to retrieve mWh value.")
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(b"Failed to retrieve mWh value.")
                        return
                except ValueError:
                    logging.error(f"Invalid latency value received: '{parts[1]}'")
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Invalid latency value.")
                    return
                except Exception as e:
                    logging.error(f"Error processing END command: {e}")
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(b"Error processing END command.")
                    return
            else:
                logging.error(f"Invalid END signal format: '{post_data}'")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid END signal format.")
                return
        else:
            logging.warning(f"Unknown command received: '{post_data}'")
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Unknown command.")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 8000

    free_port(PORT)

    try:
        logging.info("Initializing the energy meter...")
        energy_meter = GPM8310(ip_address='192.168.0.100', port='23')
        logging.info("Energy meter initialized.")
    except Exception as e:
        logging.error(f"Failed to initialize the energy meter: {e}")
        exit(1)

    try:
        with socketserver.ThreadingTCPServer((HOST, PORT), RequestHandler) as httpd:
            logging.info(f"Server started on {HOST}:{PORT}")
            logging.info("Press Ctrl+C to stop the server.")
            httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down server due to keyboard interrupt.")
    except Exception as e:
        logging.error(f"Server encountered an error: {e}")
    finally:
        if 'httpd' in locals():
            httpd.shutdown()
            httpd.server_close()
            logging.info("HTTP server shut down.")
        if 'energy_meter' in locals():
            energy_meter.close()
            logging.info("Energy meter connection closed.")


