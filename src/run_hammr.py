import tomllib
from twisted.internet import reactor, protocol

from hammr import instruments


with open('Config/system_config.toml', 'rb') as f:  # needs to run from project root
    config = tomllib.load(f)


class TestProto(protocol.Protocol):
    def __init__(self):
        print("init")

    def connectionMade(self):
        print("connected!!!")


factory = protocol.Factory()
factory.protocol = TestProto

reactor.listenTCP(9033, factory)
reactor.listenTCP(9034, factory)
reactor.listenTCP(9035, factory)

# Run servers
reactor.run()