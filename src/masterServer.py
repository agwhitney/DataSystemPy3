import json
from twisted.internet import protocol, reactor, endpoints
from twisted.protocols import basic


class ServerProtocol(basic.LineReceiver):
    def __init__(self):
        ...

    def connectionMade(self):
        # py2 does some logging and adds connection to a list,
        # but it seems like that's only used for checking that's
        # already built in
        pass

    def connectionLost(self, reason) -> None:  # type(reason) is twisted.python.failure.Failure
        # py2 logs and removes client from the unused list
        pass

    def lineReceived(self, line) -> None:
        # py2 was `dataReceived`
        match line.decode():
            case 'STOP':
                self.sendLine('stopped'.encode())
            case 'INFO':
                self.sendLine('infoed'.encode())
            case 'SYST':
                # Sends server config to client
                data = json.dumps(self.factory.system_config)
                self.sendLine(data.encode())
            case 'MSTART':
                self.sendLine('motor started'.encode())
            case 'MSTOP':
                self.sendLine('motor stopped'.encode())


class ServerFactory(protocol.Factory):
    protocol = ServerProtocol

    def __init__(self, system_config):
        self.system_config = self._load_config(system_config)

    def _load_config(self, filepath):
        with open(filepath, 'r') as f:
            config = json.load(f)
        return config


if __name__ == '__main__':
    endpoint = endpoints.serverFromString(reactor, "tcp:1079")
    endpoint.listen(ServerFactory('config/system.cfg'))
    print('lets go!')
    reactor.run()
