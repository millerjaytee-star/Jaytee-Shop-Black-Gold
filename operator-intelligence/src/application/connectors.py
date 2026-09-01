from abc import ABC,abstractmethod
class Connector(ABC):
    name='base'
    @abstractmethod
    def authenticate(self,credentials): ...
    @abstractmethod
    def fetch(self,cursor=None): ...
    @abstractmethod
    def map_to_canonical(self,records): ...
class PlannedConnector(Connector):
    def __init__(self,name): self.name=name
    def authenticate(self,credentials): raise NotImplementedError(f'{self.name} integration requires provider credentials/testing')
    def fetch(self,cursor=None): raise NotImplementedError
    def map_to_canonical(self,records): raise NotImplementedError
CONNECTORS={n:PlannedConnector(n) for n in ('toast','square','clover','7shifts','accounting','back_office')}
