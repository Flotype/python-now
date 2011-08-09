import socket, asyncore, json, eventlet

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
        name = data['name']
        args = data['args']
        if name == 'rfc':
          f = self.server.funcs[args['fqn']]
          fArgs = map(self.deserialize, args['args'], args['args'].values())
          f(*fArgs)
      except ValueError:
        print 'not valid json'
      except Exception as inst:
        print inst
  def handle_close(self):
    self.close()

  #deserialize function args to account for callbacks
  def deserialize(self, arg, val):
    if 'fqn' in arg:
      ''' TODO: Callbacks can accept callback. It accepts arguments naively here.
      Remember to serialize any python functions and put them into a closures dictionary for later retrieval '''
      return lambda *x: self.send(json.dumps({'fqn': val, 'name': 'rfc', 'args': x}))
    else:
      return val

#handle writing messages to the socket
class Sender(asyncore.dispatcher_with_send):
  def __init__(self, host, fqn, args, f=None, port = None):
    asyncore.dispatcher.__init__(self, host)
    if f:
      self.f = f
    else:
      self.f = lambda *args: self.send(json.dumps({'fqn': fqn, 'name': 'rfc', 'args': args}))

  def handle_write(self):
    try:
      self.f()
    except Exception as inst:
      print inst
    self.close()

#listens for connections
class NowPyServer(asyncore.dispatcher):
  def __init__(self, host, port):
    asyncore.dispatcher.__init__(self)
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.bind((host, port))
    self.listen(5)
    self.funcs = {}

  def handle_accept(self):
    pair = self.accept()
    if pair is None:
      pass
    else:
      sock, addr = pair
      if self.writable():
        f = lambda: self.send(json.dumps(self.funcs.keys()))
        sender = Sender(sock, None, None, f=f)
      if self.readable():
        handler = Handler(sock, self)

  def handle_close(self):
    self.close();

#register function as one that can be sent over the wire
  def register(self, name, f):
    self.funcs[name] = f

  def runserver(self):
    asyncore.loop(5)
  
server = NowPyServer('localhost', 8080)

def testFunc(s, cb):
  print s
  try:
    cb()
  except Exception as inst:
    print inst
server.register('testFunc', testFunc)

print 'now listening'
server.runserver()

''' TODO: need some way of calling a node.js function from python.
The current way it is done in ruby-now is something like val = Now.createGroupFunction(group, fqn) which returns a function.
You can then call that function and it will do the rfc'''
