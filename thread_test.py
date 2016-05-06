import thread
from time import sleep

a=5

def fnc(res):
    global a
#    print res
    a=res


thread.start_new_thread(fnc, (6,))
sleep(5)
print a

