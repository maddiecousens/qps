import argparse
import os, sys
import time

from datetime import datetime
from collections import defaultdict
from stat import ST_SIZE

import threading


class LogProcessor(object):

    PRINT_BODY = '{resource: <11}{response} {qps}'

    def __init__(self, path, print_interval):
        self.path = path
        self.print_interval = float(print_interval)
        
        # These attributes will be changed every print interval
        self.start_datetime = datetime.now().strftime("%a %b %H:%M:%S %Y")
        self.start_time = time.time()
        self._summary = defaultdict(lambda: defaultdict(int))
        self.count = 0

        # This attribute is used for the Timing thread
        self.next_call = time.time()

        # Creates an generator by calling 'tail' on the open log
        self.loglines = self.tail(LogProcessor.open_log(self.path))

    @staticmethod
    def open_log(path):
        return open(path, 'r')

    def tail(self, thefile):
        """
        Creates Generator for rotating log file.

        Detects file rotation by redution in size.
        """
        # Jump to end of file | seek(offset, from_what)
        #   from_what: 0 measures from the beg, 1 uses the current pos, 2 uses 
        #       the end of the file as reference point. 
        thefile.seek(0,2)

        while True:
            # read line, track current position
            line = thefile.readline()
            pos = thefile.tell()
            
            # If line == '', log has been rotated, or waiting on web request.
            if not line:
                # if file has been rotated, re-open
                if os.stat(self.path)[ST_SIZE] < pos:
                    # print '***ROTATING***'
                    thefile.close()
                    thefile = LogProcessor.open_log(self.path)
                    continue
                else:
                    time.sleep(0.1)
                    continue
            yield line

    def add_logline(self, resource, response):
        """
        Inputs resource and response, adds to summary default dictionary.
        """
        self._summary[resource][response] += 1
        self.count += 1

    def reset(self):
        """
        Makes call to print summary of current state of the instance, then 
        resets instance attributes.
        """
        # self.print_summary()
        self.print_summary()
        # reset
        self.start_datetime = datetime.now().strftime("%a %b %H:%M:%S:%f %Y")
        self.start_time = time.time()
        self._summary = defaultdict(lambda: defaultdict(int))
        self.count = 0

    def print_summary(self):
        """
        Prints a summary of the current state of instance:

        Timestamp
        =============
        $resource $response $average_qps
        $total

        """
        print self.start_datetime
        print '=' * 30

        for resource, response in self._summary.iteritems():
            for response, count in response.iteritems():
                print LogProcessor.PRINT_BODY.format(resource=resource,
                                                     response=response,
                                                     qps=(count / 
                                                          self.print_interval))

        print '{0: <11}{total}\n'.format('total', total=self.count)


    def process_log(self):
        """
        Processes live log file by iterating over the generator. Uses a thread
        to call reset() every [print_interval] seconds.
        """

        for line in self.loglines:
            # parse line
            resource, response = line.split()[2:-1]
            # add data to summary dictionary
            self.add_logline(resource, response)
            
            # Set thread timer for [print_interval] seconds. Account for drift
            # by subtracting off the current time. Thread calls reset(). 
            # Set as daemon, start thread.
            self.next_call = self.next_call + self.print_interval
            t = threading.Timer( self.next_call - time.time(), self.reset)
            t.daemon = True
            t.start()

def main(argv):
    """
    Takes system input, begins log reading
    """

    # Parse System input
    parser = argparse.ArgumentParser(
        description="Live log tail summary"
    )

    # Required argument, giving log file
    parser.add_argument(
        "--input-file", "-l", dest="input_file", metavar='FILE',
        type=str, required=True,
        help=(
            "the file where logs are read from"
        )
    )
    # Optional argument to set print_interval
    parser.add_argument(
        "--print-interval", "-p", dest="print_interval", metavar='SECONDS',
        type=int, required=False, default=10,
        help="How often to print summary of logs"
    )

    args = parser.parse_args(argv[1:])

    # Begin reading log
    p = LogProcessor(args.input_file, args.print_interval)
    p.process_log()

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        sys.exit()
