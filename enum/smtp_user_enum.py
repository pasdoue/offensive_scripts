#!/usr/bin/env python3

import socket
import os
import re
from colorama import Fore, Back, Style
import argparse


class SMTP_enum(object):

    def __init__(self, rhost: str, rport: int, buffer=2048):
        self.rhost = rhost
        self.rport = rport
        self.buffer = buffer
        self.smtp_options = []
        self.users = []
        self.sock = None

    def get_users(self):
        return self.users

    def connect_to_host(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(15)
            self.sock.connect((self.rhost, self.rport))
        except Exception as e:
            print(Fore.RED +"[-] Impossible to connect to remote host :("+Style.RESET_ALL)
            raise e

    def grab_banner(self, verbose=True):
        infos = self.sock.recv(self.buffer)
        if verbose:
            print(Fore.GREEN +"[+] Banner grabbing : "+Style.RESET_ALL)
            print(infos.decode().strip())

    def grab_options(self, verbose=True):
        if verbose : print(Fore.GREEN +"[+] Retrieving server options : "+Style.RESET_ALL)
        self.sock.send(b"EHLO localhost\r\n")
        self.smtp_options = [ re.sub(r'250.', '', option).strip() for option in self.sock.recv(self.buffer).decode().split("\r\n")]
        if verbose : print("\n".join(self.smtp_options))

    def guess_users(self, wordlist: str):
        if not os.path.exists(wordlist):
            raise ValueError(f"Wordlist {wordlist} does not exists")
        if "VRFY" in self.smtp_options:
            print(Fore.GREEN +"[+] Let's starts grabbing some users with VRFY option !"+Style.RESET_ALL)
            with open(wordlist, 'r') as f:
                lines = f.readlines()
            for user in lines:
                self.verify_user(username=user.strip())
        else:
            print(Fore.GREEN +"[+] Let's starts grabbing some users by crafting mail RCP TO: !"+Style.RESET_ALL)
            try:
                message = b"MAIL FROM:<> "+b'\r\n'
                self.sock.send(message)
                infos = self.sock.recv(self.buffer)
                if "OK" in infos.decode():
                    with open(wordlist, 'r') as f:
                        lines = f.readlines()
                    for user in lines:
                        self.verify_rcpt_user(username=user.strip())
            except Exception as e:
                print(Fore.RED +"[-] Impossible to find valid users from host :("+Style.RESET_ALL)
                raise e

    def verify_rcpt_user(self, username):
        if username.strip():
            try:
                message = b"RCPT TO:"+username.encode()+b'\r\n'
                # print(message)
                self.sock.send(message)
                infos = self.sock.recv(self.buffer)
                # print(infos)
            #handle connection error and reconnect to SMTP service
            except ConnectionResetError as e:
                self.sock.close()
                self.sock = None
                self.connect_to_host()
                self.grab_banner(verbose=False)
                self.sock.send(message)
                infos  = self.sock.recv(self.buffer)
            finally:
                if "250" in infos.decode() or "OK" in infos.decode():
                    print(Fore.GREEN +"[+] Found user : "+Style.RESET_ALL+Fore.YELLOW +username+Style.RESET_ALL)
                    self.users.append(username)

    def verify_user(self, username):
        message = b"VRFY "+username.encode()+b'\r\n'
        try:
            self.sock.send(message)
            infos = self.sock.recv(self.buffer)
        #handle connection error and reconnect to SMTP service
        except ConnectionResetError as e:
            self.sock.close()
            self.sock = None
            self.connect_to_host()
            self.grab_banner(verbose=False)
            self.sock.send(message)
            infos  = self.sock.recv(self.buffer)
        finally:
            if "2.0.0" in infos.decode() and username in infos.decode():
                print(Fore.GREEN +"[+] Found user : "+Style.RESET_ALL+Fore.YELLOW +username+Style.RESET_ALL)
                self.users.append(username)


parser = argparse.ArgumentParser(description='Script to enum users on remote target if VRFY is activated on remote SMTP server')
parser.add_argument('-p', '--port', default=25, type=int, help='Target port')
parser.add_argument('--host', type=str, required=True, help='IP address or simply the hostname of the target')
parser.add_argument('-w', '--wordlist', type=str, required=True, help='Wordlist used to enumerate users')

args = parser.parse_args()

smtp_grabber = SMTP_enum(rhost=args.host, rport=args.port)
smtp_grabber.connect_to_host()
smtp_grabber.grab_banner()
smtp_grabber.grab_options()
smtp_grabber.guess_users(wordlist=args.wordlist)


if smtp_grabber.get_users():
    print(Fore.GREEN +"[+] Listing users finished successfully : "+Style.RESET_ALL)
    print("\n".join(smtp_grabber.get_users()))
else:
    print(Fore.YELLOW +"[!] Found no users :( "+Style.RESET_ALL)
