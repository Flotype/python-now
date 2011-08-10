import socket, asyncore, json, eventlet
import types

#handle reading messages from the socket
class Handler(asyncore.dispatcher_with_send):
  def __init__(self, host, server, port=None):
    asyncore.dispatcher_with_send.__init__(self, host, port)
    self.server = server

  def handle_read(self):
    data = self.recv(4096)
    print data
    if(data):
      try:
        data = json.loads(data)
        print data
        name = data['type']
        if name == 'rfc':
          args = data['args']
          f = self.server.funcs[data['fqn']]
          fArgs = map(self.deserialize, args)
          f(*fArgs)
        elif name == 'closurecall':
          args = data['args']
          f = self.server.closures[data['fqn']]
          fArgs = map(self.deserialize, args)
          f(*fArgs)
        elif name == 'new':
          self.send(json.dumps({'type': 'functionList', 'functions': self.server.funcs.keys()}))
          print "Node.js server connected"

      except ValueError:
        print 'not valid json'
      except Exception as inst:
        print inst
  def handle_close(self):
    self.close()

  #deserialize function args to account for callbacks
  def deserialize(self, arg):
    if type(arg) == types.DictType and 'fqn' in arg:
      ''' TODO: Callbacks can accept callback. It accepts arguments naively here.
      Remember to serialize any python functions and put them into a closures dictionary for later retrieval '''
      return lambda *x: self.send(json.dumps({'fqn': arg['fqn'], 'type': 'closurecall', 'args': map(self.server.createCb, x)}))
    else:
      return arg

#listens for connections
class NowPyServer(asyncore.dispatcher):
  def __init__(self, host, port):
    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind((host, port))
    self.listen(5)
    self.funcs = {}
    self.closures = {}

  def handle_accept(self):
    pair = self.accept()
    if pair is None:
      pass
    else:
      sock, addr = pair
      if self.readable():
        handler = Handler(sock, self)
        self.handler = handler

  def handle_close(self):
    self.close();

#register function as one that can be sent over the wire
  def register(self, name, f):
    self.funcs[name] = f
 
  def createGroupFunction(self, group, fqn):
    return lambda *x: self.handler.send(json.dumps({'fqn': fqn, 'groupName': group, 'type': 'multicall', 'args': map(self.createCb, x)}))
    
  
  def createCb(self, arg):
    if type(arg) == types.FunctionType:
      self.closures[arg.__name__] = arg
      return {'fqn': arg.__name__} 

  def runserver(self):
    asyncore.loop()
  
server = NowPyServer('localhost', 8081)
def funcc(cb):
  fn = server.createGroupFunction("everyone", "now.callMe")
  fn(cb)

def funcb(s, cb):
  print s
  try:
    cb()
  except Exception as inst:
    print inst

server.register('b', funcb)
server.register('c', funcc)

print 'now listening'
server.runserver()


''' TODO: need some way of calling a node.js function from python.
The current way it is done in ruby-now is something like val = Now.createGroupFunction(group, fqn) which returns a function.
You can then call that function and it will do the rfc'''
