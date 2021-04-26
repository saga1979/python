import daemon
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-d", "-D", help="increase output verbosity",
                    action="store_true")
args = parser.parse_args()
if args.d or args.D:
    print("verbosity turned on")


with daemon.DaemonContext():
    with open('/tmp/zf', 'w+') as fd:
        fd.write("hello")
        print("hello")
