#!/usr/bin/env python3

import socket
import os
import re
from colorama import Fore, Back, Style
import argparse


from threading import Thread, Lock
from multiprocessing import Process, Value


def split_array(array: list, split_nb: int) -> list:
    sub_lists = []
    if split_nb > len(array):
        return [array]
    else:
        nb_sublist = len(array)//split_nb
        print(nb_sublist)
        for i in range(0, split_nb):
            sub_lists.append(array[i*nb_sublist:(i+1)*nb_sublist])
        if array[(i+1)*nb_sublist:]:
            sub_lists.append(array[(i+1)*nb_sublist:])
    return sub_lists


class SMTP_enum(object):

    def __init__(self, rhost: str, rport: int, buffer=1024):
        self.rhost = rhost
        self.rport = rport
        self.buffer = buffer
        self.smtp_options = []
        self.sock = None

        self.__connect_to_host()

    def __connect_to_host(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(15)
            self.sock.connect((self.rhost, self.rport))
        except Exception as e:
            print( Fore.RED +"[-] Impossible to connect to remote host :(" + Style.RESET_ALL )
            raise e

    def __fallback_conn(self, msg):
        """
            Try to retrieve remote connection if little disconnection occured
        """
        self.sock.close()
        self.sock = None
        self.__connect_to_host()
        self.grab_banner(verbose=False)
        self.sock.send(msg)
        return self.sock.recv(self.buffer)

    def get_smtp_options(self):
        return self.smtp_options

    def set_smtp_options(self, smtp_options):
        self.smtp_options = smtp_options

    def grab_banner(self, verbose=False):
        infos = self.sock.recv(self.buffer)
        if verbose:
            print(Fore.GREEN +"[+] Banner grabbing : "+Style.RESET_ALL)
            print(infos.decode().strip())

    def grab_options(self, verbose=False):
        if verbose : print(Fore.GREEN +"[+] Retrieving server options : "+Style.RESET_ALL)
        self.sock.send(b"EHLO localhost\r\n")
        self.smtp_options = [ re.sub(r'250.', '', option).strip() for option in self.sock.recv(self.buffer).decode().split("\r\n")]
        if verbose : print("\n".join(self.smtp_options))

    def guess_users(self, users: list, verbose=False):
        try:
            if "VRFY" in self.smtp_options:
                if verbose : print(Fore.GREEN +"[+] Let's starts grabbing some users with VRFY !"+Style.RESET_ALL)
                for user in users:
                    self.vrfy_user(username=user.strip())
            else:
                if verbose : print(Fore.GREEN +"[+] Let's starts grabbing some users by crafting mail \"RCP TO:\" !"+Style.RESET_ALL)
                self.rcpt_to_user(users=users)
            return True
        except KeyboardInterrupt:
            return

    def rcpt_to_user(self, users):
        message = b"MAIL FROM:<> "+b'\r\n'
        self.sock.send(message)
        infos = self.sock.recv(self.buffer)
        if not "OK" in infos.decode():
            return

        for username in users:
            if username.strip():
                try:
                    message = b"RCPT TO:"+username.encode()+b'\r\n'
                    # print(message)
                    self.sock.send(message)
                    infos = self.sock.recv(self.buffer)
                    # print(infos)
                #handle connection error and reconnect to SMTP service
                except ConnectionResetError as e:
                    infos  = self.__fallback_conn(msg=message)
                finally:
                    if "250" in infos.decode() or "OK" in infos.decode():
                        print(Fore.GREEN +"[+] Found user : "+Style.RESET_ALL+Fore.YELLOW +username+Style.RESET_ALL)

    def vrfy_user(self, username):
        message = b"VRFY "+username.encode()+b'\r\n'
        try:
            self.sock.send(message)
            infos = self.sock.recv(self.buffer)
        #handle connection error and reconnect to SMTP service
        except ConnectionResetError as e:
            infos  = self.__fallback_conn(msg=message)
        finally:
            if "2.0.0" in infos.decode() and username in infos.decode():
                print(Fore.GREEN +"[+] Found user : "+Style.RESET_ALL+Fore.YELLOW +username+Style.RESET_ALL)
                # append_user(username)



parser = argparse.ArgumentParser(description='Script to enum users on remote target if VRFY is activated on remote SMTP server')
parser.add_argument('-p', '--port', default=25, type=int, help='Target port')
parser.add_argument('--host', type=str, required=True, help='IP address or simply the hostname of the target')
parser.add_argument('-w', '--wordlist', type=str, required=True, help='Wordlist used to enumerate users')
parser.add_argument('-t', '--threads', type=int, required=False, default=15, help='Number of threads to spawn')

args = parser.parse_args()

if not os.path.exists(args.wordlist):
    raise ValueError(f"Wordlist {args.wordlist} does not exists")

with open(args.wordlist, 'r') as f:
    users = f.readlines()

USERS_LIST = split_array(array=users, split_nb=args.threads)
threads = []

smtp_grabber = SMTP_enum(rhost=args.host, rport=args.port)
smtp_grabber.grab_banner(verbose=True)
smtp_grabber.grab_options(verbose=True)

for i in range(len(USERS_LIST)):
    smtp_grabber = SMTP_enum(rhost=args.host, rport=args.port)
    smtp_grabber.grab_banner(verbose=False)
    smtp_grabber.grab_options(verbose=False)
    kwargs = {"users": USERS_LIST[i]}
    if i==0:
        kwargs["verbose"] = True
    proc = Process(target=smtp_grabber.guess_users, kwargs=kwargs)
    threads.append(proc)
    proc.start()

for proc in threads:
    proc.join()
