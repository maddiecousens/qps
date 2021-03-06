import argparse
import os, sys
import time

from datetime import datetime
from collections import defaultdict
# from stat import ST_SIZE

import threading


class LogProcessor(object):

    def __init__(self, path, print_interval):
        self.path = path
        self.print_interval = float(print_interval)
        
        # self.file = LogProcessor.open_log(self.path)
        self.loglines = self.tail()
        self.next_call = time.time()

    @staticmethod
    def open_log(path):
        return open(path, 'r')

    def process_log(self):
        """
        Process live log file. Read from generator.
        """

        log_chunk = LogSummary(self.path, self.print_interval)
        # @staticmethod
        # def rotate():
        #     global log_chunk
        #     log_chunk.print_summary()
        #     log_chunk = LogSummary(self.path, self.print_interval)

        

        for line in self.loglines:
            # parse line
            resource, response = line.split()[2:-1]
            # add data to dictionary
            log_chunk.add_logline(resource, response)

            # self.next_call = self.next_call + 10
            # threading.Timer( self.next_call - time.time(), rotate).start()
            
            # After print_interval, print summary, creat new log instance
            if time.time() - log_chunk.start_time > self.print_interval:
                # thread the printing
                t = threading.Thread(target=log_chunk.print_summary)
                t.start()
                log_chunk = LogSummary(self.path, self.print_interval)


    def tail(self):
        """
        Creates Generator for rotating log file.

        Detects file rotation by redution in size.
        """

        ### inode method ###
        thefile = LogProcessor.open_log(self.path)
        # curino = os.fstat(current.fileno()).st_ino

        # current.seek(0,2)

        # while True:
        #     while True:
        #         line = current.readline()
        #         if line == "":
        #             break
        #         print line

        #     try:
        #         print os.stat(self.path).st_ino, ' -- ', curino
        #         if os.stat(self.path).st_ino != curino:
        #             new = open(self.path, "r")
        #             current.close()
        #             current = new
        #             curino = os.fstat(current.fileno()).st_ino
        #             continue
        #     except IOError:
        #         pass
        #     time.sleep(0.1)

        ### filesize method ###

        thefile.seek(0,2)

        while True:
            # read line, track current position
            line = thefile.readline()
            pos = thefile.tell()
            
            # If line == '', log has been rotated, or waiting on web request.
            if not line:
                # if file has been rotated, re-open
                if os.stat(self.path).st_size < pos:
                    # print '***ROTATING***'
                    thefile.close()
                    thefile = LogProcessor.open_log(self.path)
                    continue
                else:
                    time.sleep(0.1)
                    continue
            yield line

class LogSummary(LogProcessor):
    """
    Subclass of LogProcessor

    Used to represent a time interval chunk of the log
    """

    def __init__(self, path, interval):
        LogProcessor.__init__(self, path, interval)
        self.start_datetime = datetime.now().strftime("%a %b %H:%M:%S %Y")
        self.start_time = time.time()
        self._summary = defaultdict(lambda: defaultdict(int))
        self.count = 0

    def add_logline(self, resource, response):
        """
        Input parsed log, add to summary dictionary.
        """
        self._summary[resource][response] += 1
        self.count += 1

    def print_summary(self):
        """
        Print summary dictionary.
        """
        print self.start_datetime
        print "=" * 30
        for resource, response in self._summary.iteritems():
            for response, count in response.iteritems():
                print '{}{}'.format(resource, ' ' * (10 - len(resource))), response, count / self.print_interval
        print 'total      {}\n'.format(self.count)

def main(argv):
    """
    Takes system input, begins log reading
    """

    # Parse System input
    parser = argparse.ArgumentParser(
        description="Live log tail summary"
    )

    parser.add_argument(
        "--input-file", "-l", dest="input_file", metavar='FILE',
        type=str, required=True,
        help=(
            "the file where logs are read from"
        )
    )
    parser.add_argument(
        "--print-interval", "-p", dest="print_interval", metavar='SECONDS',
        type=int, default=10,
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
