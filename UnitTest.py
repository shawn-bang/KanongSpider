# -*- coding:utf-8 -*-
import os, re, time, json, requests, random, base64, datetime, hashlib


print time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))

print os.system("cd /Users/shawnxiao/Workspace/SpiderWorkspace/kanong/ && touch a.txt")

html = "https://www.51kanong.com/yh-119-@.htm"

print html.replace("@", "1")

