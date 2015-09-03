import socket
import subprocess
import threading
import random
import string
import os
import sys

shared_memory = '/dev/shm'
openssl_path = 'openssl'

def handler(sock, addr):
  try:
    sock.settimeout(1)
    raw = sock.recv(32+512)
    data = raw[:32]
    sig = raw[32:]
    
    hisuid = os.path.join(shared_memory, ''.join(random.choice(string.ascii_letters + string.digits) for x in range(10)))
    with open(hisuid, 'wb') as f: f.write(sig)
    signed_data = subprocess.check_output([openssl_path,'rsautl','-verify','-inkey', os.path.join(shared_memory, 'main_server_public.pem'), '-in', hisuid, '-pubin'])
    os.remove(hisuid)
    if signed_data != data:
      sock.close()
      return
    
    myuid = os.path.join(shared_memory, ''.join(random.choice(string.ascii_letters + string.digits) for x in range(10)))
    with open(myuid, 'wb') as f: f.write(data)
    mysig = subprocess.check_output([openssl_path,'rsautl','-sign','-inkey', os.path.join(shared_memory, 'signing_server_private.pem') ,'-keyform','PEM', '-in', myuid])
    os.remove(myuid)
    sock.send(mysig)
    sock.close()
  except:
    sock.close()



if __name__ == "__main__":
  for arg in sys.argv:
    if arg.startswith('shared_memory='):
        shared_memory = arg.split('=')[1]
    if arg.startswith('openssl_path='):
        openssl_path = arg.split('=')[1]

  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server_address = ('0.0.0.0', 10003)
  sock.bind(server_address)
  sock.listen(100) #as many as possible
  while True:
    connection, client_address = sock.accept()
    threading.Thread(target=handler, args=(connection, client_address)).start()
    