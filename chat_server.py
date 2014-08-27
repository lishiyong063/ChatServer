#coding:utf8
import socket
import Queue
import select
import traceback
import time

class ChatServer():
    def __init__(self):
        self.dict_name = {}#客户端
        self.dict_msg = {}#消息队列
        self.listen_fd = 0#初始化监听的文件描述符
        self.inputs = []#可读状态列表
        self.outputs = []#可写状态列表
    def run(self):
        ''' 用select监听socket'''
        s = socket.socket()#默认ip tcp、协议
        s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)#地址复用
        s.bind(('localhost',10001))
        s.listen(1)
        self.inputs.append(s)#将s加入到监听的列表 
        self.listen_fd = s#将要监听的文件描述符覆给listen_fd
        while True:
            list_r,list_w,list_e = select.select(self.inputs,self.outputs,self.inputs)
            '''
                监听刚刚创建的文件描述符（inputs列表中），如果有连接到socket就select将s写到lis_r中
                如果有数据发送加入lis_w中进行操作，如果有异常在lis_e中操作
                确定第一次select检测到的状态肯定是新客户端连接进来了
            '''
            if self.listen_fd in list_r:#如果s在可写状态可能是有连接或者有数据
                conn,cli = self.listen_fd.accept()#新建一个文件描述符 来进行客户端与服务器的通信
                self.dict_name[conn] = '' #新的文件描述符加入到字典
                self.dict_msg[conn] = Queue.Queue()#将客户端加入到对应的消息队列
                self.inputs.append(conn) #将新的文件描述符加入到监听列表中
                print 'new connects',conn.getpeername() #getpeername()：获取已连接成功之 Socket 的对方位址。 
            '''
                连接成功后开始处理 select流
            '''
            self.doExcept(list_e)
            self.doRead(list_r)
            self.doWrite(list_w)
            time.sleep(0.1)
    def doRead(self,list_r=[]):
        for ts in list_r:
            if ts is self.listen_fd:continue#如果是监听的socket 就继续
            try:
                msg = ts.recv(1024) #select检查到有数据时 除了连接就是接收数据
                if msg:#如果有数据
                    print 'read[%s]'%msg
                    cmd,tmp = msg.split(None,1)#以一个空值分离一次 客户端cmd 的命令和数据
                    print 'split[%s][%s]'%(cmd,tmp) 
                    if cmd == 'name':#客户端登陆聊天室
                        self.doName(ts,tmp)
                    elif cmd == 'pm':#发送给某人
                        self.doPm(ts,tmp)
                    elif cmd == 'show':
                        self.doShow(ts,tmp)
                    else:
                        self.doMsg(ts,tmp)
                    if ts not in self.outputs:#准备发送给客户端
                        self.outputs.append(ts)
                else:
                    self.doExcept([ts])
                print 'read',ts.fileno(),len(msg) #打开文件描述符
            except:
                traceback.print_exc()
    def doWrite(self,list_w=[]):
        for ts in list_w:
            try:
                if not self.dict_msg[ts].empty():
                    msg = self.dict_msg[ts].get_nowait()#不等待，没有数据则直接引发异常
                    if msg:
                        ts.send(msg)
                    print 'write',ts.fileno(),len(msg)
            except:
                traceback.print_exc()
    def doExcept(self,list_e=[]):#异常的处理
        for ts in list_e:
            if ts in self.inputs:#如果异常则不再监听将各个队列的文件描述符删除
                self.inputs.remove(ts)
            if ts in self.outputs:
                self.outputs.remove(ts)
            if ts in self.dict_name:
                del self.dict_name[ts]
            if ts in self.dict_msg:
                del self.dict_msg[ts]
            print 'except',ts.fileno()
        
    def doName(self,ts='',tmp=''):#ts接收发过的数据 tmp 登陆聊天室
        self.dict_name[ts] = tmp#客户端对应发送的消息聊天人的姓名
        users = [k for k in self.dict_name if self.dict_name[k]] #如果连接的客户端有名字
        for s in self.dict_msg:#给聊天室每个消息队列发送一条消息
            self.dict_msg[s].put('welcome %s, there are %s friends now' % (tmp, len(users))) 

    def doMsg(self,ts='',msg=''):#群发消息
        name = self.dict_name[ts]
        for s in self.dict_msg:#新的文件描述符在消息队列中
            self.dict_msg[s].put('from %s:%s'%(name,msg))

    def doShow(self,ts='',msg=''):#查看在线人数
        users = [self.dict_name[k] for k in self.dict_name if self.dict_name[k]]
        if ts in self.dict_msg:
            msg = 'there are %s users\n %s'%(len(users),users)
            self.dict_msg[ts].put(msg)

    def doPm(self,ts='',msg=''):#对某人发
        user,tmp = msg.split(None,1)
        find_user = 0
        for s in self.dict_name:
          if self.dict_name[s] == user: #当对某人发时取得某人的消息队列
            self.dict_msg[s].put('from %s:%s' % (self.dict_name[ts], tmp))#发送用户名 消息 
            find_user = 1
            break
        if not find_user:
            self.dict_msg[ts].put('user [%s] not found, and private msg not sent successfully' % find_user)
           
if __name__=='__main__':
    cs = ChatServer()
    cs.run()
