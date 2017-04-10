from main import client
from config import config
import sys

from daemon import daemon

class MyDaemon(daemon):
    def run(self):
        client.run(config['DISCORD_BOT_TOKEN'])


if __name__ == "__main__":
    daemon = MyDaemon('/tmp/daemon-staticdiscordbot.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print("Unknown command")
            sys.exit(2)
        sys.exit(0)
    else:
        print("usage: %s start|stop|restart" % sys.argv[0])
        sys.exit(2)
