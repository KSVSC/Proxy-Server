import socket
import threading
import sys
import time
import signal
import os
import base64
#from netaddr import IPNetwork

host = ""
port = 20100
blacklist_domains = []
auth_array = []

def check_authentication():
    with open('auth.txt') as f:
        content = f.readlines()
        auth_array = [base64.b64encode(x.strip('\n')) for x in content]
        return auth_array
def blacklisting():
    with open('proxy/blacklist.txt') as f:
        content = f.readlines()
        #i = 0;
        #templen = len(content)
        #for i in range(0,templen):
        #    for ip in IPNetwork(content[i]):
        #        blacklist_domains.append(ip)

    blacklist_domains = [x.strip('\n') for x in content]
    return blacklist_domains

url_time1 = {}
url_time2 = {}
cache_time = []
cache_url = []
lock = threading.Lock()


def proxy_thread(conn,client_addr):
    request_url = conn.recv(1024)
    check_for_auth = request_url.split()
    print request_url
    temp = request_url.split('\n')
    url = temp[0].split(' ')

    http_pos = url[1].find('://')
    method_req = url[0]
    if (http_pos == -1):
        curr_url = url[1]
    else:
        curr_url = url[1][(http_pos+3):]       # get the rest of url

    port_pos = curr_url.find(":")           # find the port pos (if any)

    # find end of web server
    webserver_pos = curr_url.find("/")
    whole_url = url[1]
    reqdata = curr_url[webserver_pos:]
    main_url = curr_url[:webserver_pos]
    url[1] = reqdata
    temp[0] = " ".join(url)
    request_url = "\n".join(temp)
    if webserver_pos == -1:
        webserver_pos = len(curr_url)

    webserver = ""
    final_port = -1
    if (port_pos==-1 or webserver_pos < port_pos):      # default port
        final_port = 80
        webserver = curr_url[:webserver_pos]
    else:                                      # specific port
        final_port = int((curr_url[(port_pos+1):])[:webserver_pos-port_pos-1])
        webserver = curr_url[:port_pos]
    store_response = 0
    tempfile = open('ddd.txt','w')
    tempfile.write(request_url)
    #block the clients outside college
    if client_addr[1] > 20100 and client_addr[1] <= 20200:
        print "client ip outside college"
        conn.send("access denied\n")
        conn.close()
        sys.exit(0)

    #block if url in blacklisted domains
    if main_url in blacklist_domains:
        if "Basic" in check_for_auth:
            if check_for_auth[check_for_auth.index("Basic")+1] in auth_array:
                pass
            else:
                print "unauthenticated"
                conn.send("Un authenticated\n")
                conn.close()
                sys.exit(0)
        else:
            print "domain is blacklisted"
            conn.send('HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n<!doctype html>\n<html>\n<body>\n<h1>Cannot access this domain<h1>\n</body>\n</html>\n')
            conn.close()
            sys.exit(0)
    #first check whether url is present in cache
    lock.acquire()
    if whole_url in cache_url and method_req == "GET":
        #send requests add if modified since.
        index_to_be_updated = cache_url.index(whole_url)
        temp1 = request_url.split('\n')
        time_for_that_cache = cache_time[index_to_be_updated]
        ran_var1 = time.ctime(time_for_that_cache)
        ran_var2 = ran_var1.split()
        #ran_var2[1],ran_var2[2] = ran_var2[2],ran_var2[1]
        #ran_var2[3],ran_var2[4] = ran_var2[4],ran_var2[3]
        require_to_add_last_update_time =  " %s %s %s %s GMT %s" %(ran_var2[0],ran_var2[1],ran_var2[2],ran_var2[3],ran_var2[4])
        print temp1
        ran_var3 = "If-Modified-Since:" + require_to_add_last_update_time+"\n"
        dum_val1 = temp1.pop()
        dum_val2 = temp1.pop()
        temp1.append(ran_var3)
        temp1.append(dum_val2)
        temp1.append(dum_val1)
        request_url = "\n".join(temp1)
        print request_url
        store_response = 2
        lock.release()
    else:
        lock.release()  #unlock cache and again acquire lock for checking in recently searched urls
        lock.acquire()
        if method_req == "GET":
            curr_time = time.time()
            if url_time1.get(whole_url) == None:
                url_time1[whole_url] = curr_time
            else:
                if curr_time - url_time1[whole_url] < 300:
                    if url_time2.get(whole_url) == None:
                        url_time2[whole_url] = curr_time
                    else:
                        url_time1[whole_url] = url_time2[whole_url]
                        url_time2[whole_url] = curr_time
                        if len(cache_url)<3:
                            cache_url.append(whole_url)
                            cache_time.append(curr_time)
                        else :
                            if curr_time > min(cache_time):
                                index_to_be_updated = cache_time.index(min(cache_time))
                                ran_var4 = cache_url[index_to_be_updated].split('/')
                                os.remove(ran_var4[3])
                                cache_time[index_to_be_updated] = curr_time
                                cache_url[index_to_be_updated] = whole_url
                else:
                    if url_time2.get(whole_url) == None:
                        url_time1[whole_url] = curr_time
                    else:
                        if curr_time - url_time2[whole_url] > 300:
                            url_time1[whole_url] = curr_time
                        else:
                            url_time1[whole_url] = url_time2[whole_url]
                            url_time2[whole_url] = curr_time
        if whole_url in cache_url and method_req == "GET":
            print reqdata[1:]
            temp_file = open(reqdata[1:],"w+")
            store_response = 1
        lock.release()


    try:
        main_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        main_s.settimeout(5)
        main_s.connect((webserver,final_port))
        main_s.sendall(request_url)
        whole_response = ""#store response for if modified since part
        while True:
            try:
                conn.settimeout(1)
                data = main_s.recv(1024)
                conn.settimeout(None)
            except:
                conn.settimeout(None)
                break
            if (data != ""):
                whole_response =whole_response+data
                if store_response == 1:
                    temp_file.write(data)
            else:
                break
        if store_response == 0:
            tempfile.write(whole_response)
            tempfile.close()
            conn.send(whole_response)
        if store_response == 1:
            tempfile.write(whole_response)
            tempfile.close()
            conn.send(whole_response)
            temp_file.close()
        if store_response == 2:
            ran_var5 = whole_response.split()
            print whole_response
            if "304" in ran_var5:
                with open(reqdata[1:]) as f:
                    content = f.read()
                    tempfile.write(content)
                    tempfile.close()
                    conn.send(content)
            elif "200" in ran_var5:
                with open(reqdata[1:],"w") as f:
                    tempfile.write(whole_response)
                    tempfile.close()
                    f.write(whole_response)
                    conn.send(whole_response)
        main_s.close()
        conn.close()
    except socket.error as error_msg:
        print "ERROR:",addr,error_msg
        if main_s:
            main_s.close()
        if conn:
            conn.close()



try:
    server_s = socket.socket()
    server_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
except:
    print "failed to create socket"
    sys.exit()
print "socket created"
try:
    server_s.bind((host,port))
except:
    print "bind failed"
    sys.exit()
try:
    server_s.listen(10)
except:
    print "failed to listen"
    sys.exit()
print "server listening..."
blacklist_domains = blacklisting()
auth_array = check_authentication()

while True:
    conn,addr = server_s.accept()
    new_thread = threading.Thread(name = "Client", target = proxy_thread ,args = (conn,addr))
    new_thread.setDaemon(True)
    new_thread.start()
