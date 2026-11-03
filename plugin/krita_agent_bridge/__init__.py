from krita import Krita, Extension


class KritaAgentBridge(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        pass


Krita.instance().addExtension(KritaAgentBridge(Krita.instance()))
