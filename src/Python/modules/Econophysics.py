import tweepy
import json
import pickle
from datetime import datetime,timezone
import time
from threading import Thread
import numpy as np
import random
import matplotlib.pyplot as plt 
import seaborn as sns
import statsmodels
import math
import powerlaw as pwl
from collections import Counter, defaultdict
import os
import networkx as nx 
#import EoN     
import copy
import traceback 
import sys
from urllib3.exceptions import ProtocolError
import ast
from IPython.display import clear_output

def split_array(ary, indices_or_sections):
    return np.array_split(ary =ary, indices_or_sections = indices_or_sections)


class TwitterThreadOBJ(Thread):
    
    #printer = Printer(2)
    
    def __init__(self,name,apps,ids,path, resource_remaining, resource_reset, restart = False ): #here
        Thread.__init__(self)
        self.name    = name
        self.apps    = apps
        self.ids     = ids
        self.path    = path
        self.restart = restart
        
        self.resource_remaining = resource_remaining
        self.resource_reset = resource_reset
        
        self.mode = "user"
        
    def get_info(self):
        print(self.name,":\n\t path: ",self.path,"\n\t restart:", self.restart,"\n\t mode",self.mode,"\n")
    
    def utc_s(self): #https://stackoverflow.com/questions/5998245/get-current-time-in-milliseconds-in-python
        return round(datetime.utcnow().timestamp()) + (60*60*2)

    def logger(self,credentials,mode, wait_on_rate_limit = True):
        total = len(self.ids)
        retry_count = 1
        retry_delay = 5
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")

    # Fields of user object that we may use to estimate activity: location':"", 'profile_location'=None, 'protected':False,'followers_count': 17,'friends_count': 197,'created_at': 'Sat Sep 28 23:13:30 +0000 2019', 'favourites_count': 28,'statuses_count': 1,follow_request_sent=False

    def get_limits(self,app,path = None):
        limits = app.rate_limit_status()
        if path is not None:
            limit = limits
            for branch in path: 
                limit = limit[branch]
            return limit
        else:
            return limits
        
        
    def test(self,mode = "user",screen_name = "ClaudioMoroni3"):
        i = 0
        apps = self.logger(self.apps, mode = mode ,wait_on_rate_limit = False)
        for app in apps:
            try:
                user = app.get_user(screen_name = screen_name)
                print("app number",i,"authentication succeded")
                i +=1
            except tweepy.TweepError as e:
                print("app number",i,"authentication failed, with reason:", e.response.text)
                i +=1
                
    def loader(self,path):
        with open(path, "rb") as f:
            objs = []
            while 1:
                try:
                    objs.append(pickle.load(f))
                except EOFError:
                    break
            f.close()

        objs = [x for y in objs for x in y]
        print(len(objs))


        return np.array(objs)
                
    def run(self):
        #apps = self.apps
        n = 0
        self.mode = "user"
        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
        appFail = False
        i = 0
        to_be_written = []
        all_used = False
        index = 0
        if os.path.exists(self.path) and self.restart:
            try:
                already_downloaded_objs = self.loader(self.path)
                last_id = already_downloaded_objs[-1]["user_id"]
                #print("last_id = ",last_id )
                index = np.where(self.ids == last_id)[0][0] + 1
                all_used = True
            except _pickle.UnpicklingError as e:
                print(self.name, ": File",self.path, " corrupted, delete that file. The thread will start from index = 0 writing in a new file called",self.path[:-4]+"_new.txt \n")
                index = 0 
                self.path = self.path[:-4]+"_new.txt"
            
        total = len(self.ids[index:])
        print(self.name,"started. Downloading user objects from user_id",self.ids[index], "to",self.ids[-1],"so we start from index",index,"\n")
        for user_id in self.ids[index:]:
            while True:
                try:
                    user = app.get_user(user_id = user_id)
                    CE_times = 0
                    dct = {"user_id":user_id,'followers_count': user.followers_count,'friends_count': user.friends_count,'created_at': str(user.created_at), 'favourites_count': user.favourites_count,'statuses_count': user.statuses_count}
                    to_be_written.append(dct) #dct
                    i = i+1
                    if self.name == "thread10":
                        print(self.name,": downloaded",i," -th user object ( user_id = ",user_id,") out of",total,"total, with app number",n,end = "\r") #TwitterThread.printer.thread_print(self.name + " ; done: "+ str(i) +" with id " + str(user_id)) #print(self.name,"; done:",i,"with id",user_id,end = "\r")
                    break
                except tweepy.RateLimitError:
                    if len(to_be_written) >0:
                        with open(self.path, "ab") as f: # see https://stackoverflow.com/questions/36965507/writing-a-dictionary-to-a-text-file
                            pickle.dump(to_be_written, f) # f.write(pickle.dumps(dct)) json.dumps(user). Actually saving it as a string or serialized is equally slow
                            to_be_written = []
                            #print(self.name,":written up to",i,"-th user whose id is ",user_id)
                    if not appFail : #mode == "user" and
                        #print("App number",n,"with user auth depleted, authenticationg as app...")
                        self.mode  = "app"
                        app = self.logger(self.apps[n],mode = self.mode ,wait_on_rate_limit = False)
                        remaining = self.get_limits(app,self.resource_remaining)
                        #print("remaining = ", remaining)
                        if remaining == 0 and all_used:
                            wait = self.get_limits(app,self.resource_reset) - self.utc_s()
                            if self.name == "thread10":
                                print(self.name,";sleeping", wait + 10, " seconds to ensure timers are reset...", end = "\n")
                            time.sleep(wait + 10)
                        appFail = True
                        continue
                    else:
                        self.mode  = "user"
                        #print(self.name,"Also app auth of",n,"-th app has been depleted. Switching to next app...")
                        if n == len(self.apps)-1:
                            #if self.name == "thread1":
                                #print("last app was actually depleted. Restarting from n = 0....",end = "\r")
                            n = 0
                            all_used = True
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0:
                                wait = self.get_limits(app,self.resource_reset)-self.utc_s()
                                if self.name == "thread10":
                                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                time.sleep(wait + 10)
                        else:
                            n = n+1
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0 and all_used:
                                wait = self.get_limits(app,self.resource_reset)-self.utc_s()
                                if self.name == "thread10":
                                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                time.sleep(wait + 10)
                        appFail = False
                        continue
                except ConnectionError as e:
                    if CE_times < 5:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,"\nRelogging the app number",n," for the",CE_times,"time.\n ")
                        time.sleep(5)
                        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                        CE_times += 1
                        continue
                    else:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,". Tried to reconnect for 5 times in a row without success. Skipping user... ")
                        break                
                except tweepy.TweepError as e:
                    if e.api_code == 50: #https://stackoverflow.com/a/48499300 #https://www.programcreek.com/python/?code=SMAPPNYU%2FsmappPy%2FsmappPy-master%2FsmappPy%2Ftweepy_pool.py#   #https://github.com/tweepy/tweepy/issues/1254
                        i = i+1
                        #print("User",user_id,"not found, skipping...")
                        break
                    else:
                        #print("caught unknown tweepError for user",user_id,": \n",e.response.text,"\nskipping...")
                        i = i+1
                        break
                except Exception as e:
                    print(self.name,": Exception occurred at user", user_id,"with app number",n)
                    raise e
        #TwitterThread.printer.thread_print("finished")
        with open(self.path, "ab") as f: # see https://stackoverflow.com/questions/36965507/writing-a-dictionary-to-a-text-file
            pickle.dump(to_be_written, f) # f.write(pickle.dumps(dct)) json.dumps(user). Actually saving it as a string or serialized is equally slow
            to_be_written = []
        print(self.name,"FINISHED!!! \n")



class TwitterThreadRW(Thread):
    
    #printer = Printer(2)
    
    def __init__(self,name,apps,path,ids,resource_remaining,resource_reset, print_thread = "thread1", target = None, restart = False): #all users is the list of all boris & corbyn followers
        Thread.__init__(self)
        self.name = name # name of the rhread
        self.apps = apps # list of lists of two dicts containing credentials
        self.path = path # where to save downloaded informations
        self.ids = ids #all users' ids downloaded with TwitterThread
        self.resource_remaining = resource_remaining
        self.resource_reset = resource_reset
        self.print_thread = print_thread
        if target is not None:
            self.target = target
        else:
            self.target = len(self.ids)
        
        self.all_downloaded = np.array([]) # all users ids downloaded with this script
        self.all_downloaded_jumped = np.array([]) # all users ids downloaded with this script except those who were used to jump
        self.flows = 0 # how many time the random flow has been respected
        self.withdraws = 0 # how many time the script had to jump to a previously downloaded user because of lack of followers of the just followers-scraped user
        self.jumps = 0 # how many time the script had to perform a random jump
        self.walked_users = []
        self.loop = 0
        
        
    # get current utc + 2hours time in seconds
    def utc_s(self): #https://stackoverflow.com/questions/5998245/get-current-time-in-milliseconds-in-python
        return round(datetime.utcnow().timestamp()) + (60*60*2)
    
    # log one or multiple apps
    def logger(self,credentials,mode, wait_on_rate_limit = False):
        retry_count = 1
        retry_delay = 5
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")

    # Fields of user object that we may use to estimate activity: location':"", 'profile_location'=None, 'protected':False,'followers_count': 17,'friends_count': 197,'created_at': 'Sat Sep 28 23:13:30 +0000 2019', 'favourites_count': 28,'statuses_count': 1,follow_request_sent=False
    
    # get remaining availabel calls to a specifc Twitter APi for the current app
    def get_limits(self,app,path = None):
        limits = app.rate_limit_status()
        if path is not None:
            limit = limits
            for branch in path: 
                limit = limit[branch]
            return limit
        else:
            return limits
        
    # test all apps assigned to this thread work
    def test(self,mode = "user",screen_name = "ClaudioMoroni3"):
        i = 0
        apps = self.logger(self.apps, mode = mode ,wait_on_rate_limit = False)
        for app in apps:
            try:
                user = app.get_user(screen_name = screen_name)
                print("app number",i,"authentication succeded")
                i +=1
            except tweepy.TweepError as e:
                print("app number",i,"authentication failed, with reason:", e.response.text)
                i +=1
    
    # remove user from a 1d numpy array of ids and return the remaining array
    def remove_user(self,arr,user):
        return np.delete(arr,np.where(arr == user))
    
    def loader(self):
        with open(self.path, "rb") as f:
            objs = []
            while 1:
                try:
                    objs.append(pickle.load(f))
                except EOFError:
                    break
            f.close()


        return objs
            
    
    # get next user, either following th flow, withdrawing ar random jumping
    def next_user(self,app,fllwrs):
        found_next = False
        while len(fllwrs) > 0:
            try:
                choice = int(random.choice(fllwrs))
                current_user = app.get_user(user_id = choice )
                fllwrs.remove(current_user.id)
                if current_user.followers_count > 0:
                    found_next = True
                    self.flows += 1
                    current_user = int(current_user.id)
                    break
            except tweepy.TweepError as e:
                #print("next_user flow; User",choice,"private/inexistent/suspended:",e.response.text," skipping...\n")
                fllwrs.remove(current_user.id)
                continue
        if not found_next:
            while(len(self.all_downloaded_jumped)) > 0:
                try:
                    choice = int(random.choice(self.all_downloaded_jumped))
                    current_user = app.get_user(user_id =choice )
                    self.all_downloaded_jumped = self.remove_user(self.all_downloaded_jumped,choice)
                    if current_user.followers_count > 0:
                        found_next = True
                        self.withdraws += 1
                        current_user = int(current_user.id)
                        break
                except tweepy.TweepError as e:
                    #print("next_user withdraw; User",choice,"private/inexistent/suspended:",e.response.text," skipping...\n")
                    self.all_downloaded_jumped = self.remove_user(self.all_downloaded_jumped,choice)
                    continue
        if not found_next:
            while len(self.ids) > 0:
                try:
                    current_user = random.choice(self.ids)
                    self.ids = self.remove_user(self.ids,current_user)
                    if int(current_user["followers_count"]) > 0:
                        current_user = int(current_user["user_id"])
                        found_next = True
                        self.jumps += 1
                        break
                except tweepy.TweepError as e:
                    #print("next_user jump; User",current_user["user_id"],"private/inexistent/suspended:",e.response.text," skipping...\n")
                    self.ids = self.remove_user(self.ids,current_user)
                    continue
        if found_next:
            return current_user
        else:
            return None
    
    # the main thread method
    def run(self):
        #apps = self.apps
        n = 0
        mode = "user"
        app = self.logger(self.apps[n],mode = mode, wait_on_rate_limit = False)
        appFail = False
        i = 0
        to_be_written = []
        all_used = False
        
        current_user = random.choice(self.ids)
        #if self.target is
        #target = len(self.ids)
        self.ids = self.remove_user(self.ids,current_user)
        current_user = int(current_user["user_id"])
        #already_walked = False
        
        
        while len(self.all_downloaded) <= self.target : #target
            if self.loop > len(self.walked_users):
                print(" \n entered loop of size",self.loop,"while total of walked users is,",len(self.walked_users),", exiting...\n")
                break
            to_be_written = []
            fllwrs = []
            if current_user not in self.walked_users:
                self.loop = 0
                cursor = -1
                while cursor != 0:
                    failed = False
                    try:
                        itr = tweepy.Cursor(app.followers_ids, user_id=current_user, cursor=cursor).pages() # an alternative would  be this : itr = tweepy.Cursor(app.followers, screen_name="BorisJohnson").items(). itr would tehn be an iterabe ocntaining 15 * 20 user objects of follwers, before launching  a rate limit error and forcing to re-log as app, which gives you other 15 * 20 objects to download. Too few, i think we will be faster off combining TwitterThreadRW and TwitterThread. It would consume ["resources","followers","/followers/list"] resource.
                        for fllwr in itr.next():
                            fllwrs.append(fllwr)

                        cursor = itr.next_cursor
                    except tweepy.RateLimitError:
                        if not appFail : #mode == "user" and
                            #print("App number",n,"with user auth depleted, authenticationg as app... \n")
                            app = self.logger(self.apps[n],mode = "app",wait_on_rate_limit = False)
                            remaining = self.get_limits(app,path = self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0 and all_used:
                                wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                if self.name == self.print_thread:
                                    print("\n",self.name," : sleeping", wait + 10, " seconds to ensure timers are reset... \n") #, end = "\r"
                                time.sleep(wait + 10)
                            appFail = True
                            continue
                        else:
                            #print(self.name,"Also app auth of",n,"-th app has been depleted. Switching to next app... \n")
                            if n == len(self.apps)-1:
                                #if self.name == "thread1":
                                    #print("last app was actually depleted. Restarting from n = 0.... \n") #,end = "\r"
                                n = 0
                                all_used = True
                                app = self.logger(self.apps[n],mode = "user", wait_on_rate_limit = False)
                                remaining = self.get_limits(app,path = self.resource_remaining)
                                #print("remaining = ", remaining)
                                if remaining == 0:
                                    wait = self.get_limits(app,path = self.resource_reset)-self.utc_s()
                                    if self.name == self.print_thread:
                                        print("\n",self.name," : sleeping",wait + 10," seconds to ensure timers are reset...\n") #,end = "\r"
                                    time.sleep(wait + 10)
                            else:
                                n = n+1
                                app = self.logger(self.apps[n],mode = "user", wait_on_rate_limit = False)
                                remaining = self.get_limits(app,path = self.resource_remaining)
                                #print("remaining = ", remaining)
                                if remaining == 0 and all_used:
                                    wait = self.get_limits(app,path = self.resource_reset)-self.utc_s()
                                    if self.name == self.print_thread:
                                        print("\n",self.name," : sleeping",wait + 10," seconds to ensure timers are reset...\n") #,end = "\r"
                                    time.sleep(wait + 10)
                            appFail = False
                            continue
                    except tweepy.TweepError as e:
                        #if e.args[0][0]['code'] == 50:
                        i = i+1
                        failed = True
                        #print("run; User",current_user,"private/inexistent/suspended:",e.response.text," skipping...\n")
                        break
                    except Exception as e:
                        failed = True
                        #print(self.name,": Exception occurred at user", current_user,"with app number",n)
                        raise
                    #cursor = itr.next_cursor
                if not failed:
                    to_be_written = [current_user,fllwrs] #dct
                    news = np.array([fllwr for fllwr in fllwrs if fllwr not in self.all_downloaded])
                    #print("len(fllwrs) = ",len(fllwrs),"\n" )
                    #print("len(self.all_downloaded) = ",len(self.all_downloaded),"\n" )
                    #print("len(news) = ", len(news),"\n")
                    self.all_downloaded = np.concatenate((self.all_downloaded,news))
                    self.all_downloaded_jumped = np.concatenate((self.all_downloaded_jumped,news))
                    with open(self.path, "ab") as f: # see https://stackoverflow.com/questions/36965507/writing-a-dictionary-to-a-text-file
                        pickle.dump(to_be_written, f) # f.write(pickle.dumps(dct)) json.dumps(user). Actually saving it as a string or serialized is equally slow
            else:
                rw_ids = self.loader() 
                for couple in rw_ids:
                    if couple[0] == current_user:
                        fllwrs = couple[1]
                        break
                self.loop += 1
                del rw_ids
                
            self.walked_users.append(current_user)
            current_user = self.next_user(app,fllwrs)
#             if current_user in self.walked_users:
#                 already_walked = True
#             else:
#                 already_walked = False
                
            
            # should it go bad...
            if current_user is None:
                print("incredibly, no users with more than 0 followers were found, not even jumping. Stopping...")
                break
            
            i = i+1
            if self.name == "thread1":
                print(self.name,": downloaded ",len(self.all_downloaded)," users out of",self.target,"total, from",self.flows,"rw steps,",self.withdraws,"withdraws and",self.jumps," jumps. Currently using with app number",n,"and current_user is",current_user,". Current loop size is ",self.loop,end = "\r") 
        print(self.name,"FINISHED!!! \n")
        
        


        
        
# takes an ids list and returns their followers, form which you may build the follower network.
# change line " itr = tweepy.Cursor(app.followers_ids, user_id=user_id, cursor=cursor).pages()" of run method to " itr = tweepy.Cursor(app.followers_ids, screen_name=user_id, cursor=cursor).pages()" to use screen_names. If you want to get all the folllwers of  single person, then comment this block:
#if self.name == "thread1":
#    print(self.name,": downloaded ",i," followers sets out of",total,"total. Currently using with app number",n,"and the last user_id was",user_id,end = "\r") 

#in run method and add this one
#if self.name == "thread1":
#   print(self.name,": downloaded ",len(fllwrs)," followers Currently using with app number",n,end = "\r") 

#immediatly after #except tweepy.RateLimitError:.
    
class TwitterThreadFLLWRS(Thread):
    
    #printer = Printer(2)
    
    def __init__(self,name,apps,ids,path,resource_remaining,resource_reset, restart = False): #here
        Thread.__init__(self)
        self.name = name
        self.apps = apps
        self.ids = ids
        self.path = path
        self.restart = restart
        self.resource_remaining = resource_remaining
        self.resource_reset = resource_reset
        self.writing_thread = "thread0"
        
        self.mode  = "user"
    
    def utc_s(self): #https://stackoverflow.com/questions/5998245/get-current-time-in-milliseconds-in-python
        return round(datetime.utcnow().timestamp()) + (60*60*2)

    def logger(self,credentials,mode, wait_on_rate_limit = True):
        total = len(self.ids)
        retry_count = 1
        retry_delay = 5
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")

    # Fields of user object that we may use to estimate activity: location':"", 'profile_location'=None, 'protected':False,'followers_count': 17,'friends_count': 197,'created_at': 'Sat Sep 28 23:13:30 +0000 2019', 'favourites_count': 28,'statuses_count': 1,follow_request_sent=False

    def get_limits(self,app,path = None):
        limits = app.rate_limit_status()
        if path is not None:
            limit = limits
            for branch in path: 
                limit = limit[branch]
            return limit
        else:
            return limits
        
        
    def test(self,mode = "user",screen_name = "ClaudioMoroni3"):
        i = 0
        apps = self.logger(self.apps, mode = mode ,wait_on_rate_limit = False)
        for app in apps:
            try:
                user = app.get_user(screen_name = screen_name)
                print("app number",i,"authentication succeded")
                i +=1
            except tweepy.TweepError as e:
                print("app number",i,"authentication failed, with reason:", e.response.text)
                i +=1

    # loads and returns user-followers list of type [[user1,[user1_follower1,user1_follower2,...]],[user2,[user2_follower1,user2_follower2,...]],...]
    def followers_loader(self): #inspired by rw_to_TwitterThread
        with open(self.path, "rb") as f:
            rw_ids_raw = []
            while 1:
                try:
                    rw_ids_raw.append(pickle.load(f))
                except EOFError:
                    break
            f.close()
        return np.array(rw_ids_raw)
                
    def run(self):
        #apps = self.apps
        n = 0
        #mode = "user"
        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
        appFail = False
        i = 0
        to_be_written = []
        all_used = False
        index = 0
        if os.path.exists(self.path) and self.restart:
            try:
                already_downloaded_objs = self.followers_loader()
                last_id = already_downloaded_objs[-1][0]
                #print("last_id = ",last_id )
                index = np.where(self.ids == last_id)[0][0] + 1
                all_used = True
            except _pickle.UnpicklingError as e:
                print(self.name, ": File",self.path, " corrupted, delete that file. The thread will start from index = 0 writing in a new file called",self.path[:-4] + "_new.txt \n")
                index = 0 
                self.path = self.path[:-4] + "_new.txt"
            
        total = len(self.ids[index:])
        print(self.name,"started. Downloading user objects from user_id",self.ids[index], "to",self.ids[-1],"so we start from index",index,"\n")
        
        for user_id in self.ids[index:]:
            cursor = -1
            fllwrs = []
            terminate = False
            while True:
                try:
                    while cursor != 0:
                        failed = False
                        try:
                            itr = tweepy.Cursor(app.followers_ids, user_id=user_id, cursor=cursor).pages() # an alternative would  be this : itr = tweepy.Cursor(app.followers, screen_name="BorisJohnson").items(). itr would tehn be an iterabe ocntaining 15 * 20 user objects of follwers, before launching  a rate limit error and forcing to re-log as app, which gives you other 15 * 20 objects to download. Too few, i think we will be faster off combining TwitterThreadRW and TwitterThread. It would consume ["resources","followers","/followers/list"] resource.
                            CE_times = 0
                            for fllwr in itr.next():
                                fllwrs.append(fllwr)

                            cursor = itr.next_cursor


                        except tweepy.RateLimitError:
        #                     if len(to_be_written) >0:
        #                         with open(self.path, "ab") as f: # see https://stackoverflow.com/questions/36965507/writing-a-dictionary-to-a-text-file
        #                             pickle.dump(to_be_written, f) # f.write(pickle.dumps(dct)) json.dumps(user). Actually saving it as a string or serialized is equally slow
        #                             to_be_written = []
                                    #print(self.name,":written up to",i,"-th user whose id is ",user_id)
                            if not appFail : #mode == "user" and
                                #print("App number",n,"with user auth depleted, authenticationg as app...")
                                self.mode  = "app"
                                app = self.logger(self.apps[n],mode = self.mode,wait_on_rate_limit = False)
                                remaining = self.get_limits(app,path = self.resource_remaining)
                                #print("remaining = ", remaining)
                                if remaining == 0 and all_used:
                                    wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                    if self.name == self.writing_thread:
                                        print(self.name,";sleeping", wait + 10, " seconds to ensure timers are reset...", end = "\n")
                                    time.sleep(wait + 10)
                                appFail = True
                                continue
                            else:
                                self.mode  = "user"
                                #print(self.name,"Also app auth of",n,"-th app has been depleted. Switching to next app...")
                                if n == len(self.apps)-1:
                                    #if self.name == "thread1":
                                        #print("last app was actually depleted. Restarting from n = 0....",end = "\r")
                                    n = 0
                                    all_used = True
                                    app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                                    remaining = self.get_limits(app,path = self.resource_remaining)
                                    #print("remaining = ", remaining)
                                    if remaining == 0:
                                        wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                        if self.name == self.writing_thread:
                                            print(self.name,"sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                        time.sleep(wait + 10)
                                else:
                                    n = n+1
                                    app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                                    remaining = self.get_limits(app,path = self.resource_remaining)
                                    #print("remaining = ", remaining)
                                    if remaining == 0 and all_used:
                                        wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                        if self.name == self.writing_thread:
                                            print(self.name,"sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                        time.sleep(wait + 10)
                                appFail = False
                                continue
                        except ConnectionError as e:
                            print("\n",self.name, "Caught a  ConnectionError, with reason:\n", e.reason,"\nRelogging the app number",n," for the",CE_times,"time.\n ")
                            time.sleep(2)
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            CE_times += 1
                        except tweepy.TweepError as e: #this type of erorr: tweepy.error.TweepError: Failed to send request: ('Connection aborted.', OSError("(10053, 'WSAECONNABORTED')")) is caught here
                            if e.api_code == 50: #https://stackoverflow.com/a/48499300 #https://www.programcreek.com/python/?code=SMAPPNYU%2FsmappPy%2FsmappPy-master%2FsmappPy%2Ftweepy_pool.py#   #https://github.com/tweepy/tweepy/issues/1254
                                i = i+1
                                failed = True
        #                         if self.name == "thread1":
                                print("\n",self.name,"User",user_id,"not found, skipping...")
                                break
                            else:
                                print("\n",self.name," caught unknown tweepError for user",user_id,": \n","\nskipping...") #,e.response.text
                                failed = True
                                #i = i+1
                                break
                        except StopIteration:
                            print(self.name, ": StopIteration caught, skipping....", "len(fllwrs)=",len(fllwrs), "cursor = ", cursor  )
                            break
                        except Exception as e:
                            print(self.name,": Exception occurred at user", user_id,"with app number",n)
                            failed = True
                            raise e
                    if not failed:
                        #to_be_written = [user_id,fllwrs] #dct
                        to_be_written = {"user_id": user_id, "followers_ids":fllwrs}
                        #news = np.array([fllwr for fllwr in fllwrs if fllwr not in self.all_downloaded])
                        #print("len(fllwrs) = ",len(fllwrs),"\n" )
                        #print("len(self.all_downloaded) = ",len(self.all_downloaded),"\n" )
                        #print("len(news) = ", len(news),"\n")
                        #self.all_downloaded = np.concatenate((self.all_downloaded,news))
                        #self.all_downloaded_jumped = np.concatenate((self.all_downloaded_jumped,news))
                        with open(self.path, "ab") as f: # see https://stackoverflow.com/questions/36965507/writing-a-dictionary-to-a-text-file
                            f.write(pickle.dumps(to_be_written))
                            #pickle.dump(to_be_written, f) # f.write(pickle.dumps(dct)) json.dumps(user). Actually saving it as a string or serialized is equally slow


                    i = i+1
                    if self.name == self.writing_thread:
                        print(self.name,": downloaded ",i," followers sets out of",total,"total. Currently using with app number",n,"and the last user_id was",user_id,end = "\r") 
                    break
                except ConnectionError as e:
                    if CE_times < 5:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,"\nRelogging the app number",n," for the",CE_times,"time.\n ")
                        time.sleep(5)
                        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                        CE_times += 1
                        continue
                    else:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,". Tried to reconnect for 5 times in a row without success. The user_id during which the exception occured was",user_id,". Exiting...")
                        terminate = True
                        break
            # if for 5 times (spaced bt 5 seconds) teh app couldent reconnect follwing a ConnectionError exception, terminate the thread            
            if terminate:
                break
            
        print(self.name,"FINISHED!!! \n")



 


class TwitterThreadRTWT(Thread):
    
    #printer = Printer(2)
    
    def __init__(self,name,apps,ids,path,resource_remaining,resource_reset,target_date = None, restart = False): #here
        Thread.__init__(self)
        self.name = name
        self.apps = apps
        self.ids = ids
        self.path = path
        self.restart = restart
        self.resource_remaining = resource_remaining
        self.resource_reset = resource_reset
        
        if target_date is not None:
            self.target_date = target_date
        else:
            self.target_date = datetime.strptime("01-01-1970 00:00:00", "%d-%m-%Y %H:%M:%S")
        
        self.mode  = "user"
    
    def utc_s(self): #https://stackoverflow.com/questions/5998245/get-current-time-in-milliseconds-in-python
        return round(datetime.utcnow().timestamp()) + (60*60*2)

    def logger(self,credentials,mode, wait_on_rate_limit = True):
        total = len(self.ids)
        retry_count = 1
        retry_delay = 5
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")

    # Fields of user object that we may use to estimate activity: location':"", 'profile_location'=None, 'protected':False,'followers_count': 17,'friends_count': 197,'created_at': 'Sat Sep 28 23:13:30 +0000 2019', 'favourites_count': 28,'statuses_count': 1,follow_request_sent=False

    def get_limits(self,app,path = None):
        limits = app.rate_limit_status()
        if path is not None:
            limit = limits
            for branch in path: 
                limit = limit[branch]
            return limit
        else:
            return limits
        
        
    def test(self,mode = "user",screen_name = "ClaudioMoroni3"):
        i = 0
        apps = self.logger(self.apps, mode = mode ,wait_on_rate_limit = False)
        for app in apps:
            try:
                user = app.get_user(screen_name = screen_name)
                print("app number",i,"authentication succeded")
                i +=1
            except tweepy.TweepError as e:
                print("app number",i,"authentication failed, with reason:", e.response.text)
                i +=1

    # loads and returns user-followers list of type [[user1,[user1_follower1,user1_follower2,...]],[user2,[user2_follower1,user2_follower2,...]],...]
    def followers_loader(self): #inspired by rw_to_TwitterThread
        with open(self.path, "rb") as f:
            rw_ids_raw = []
            while 1:
                try:
                    rw_ids_raw.append(pickle.load(f))
                except EOFError:
                    break
            f.close()
        return np.array(rw_ids_raw)
    
    
    def dct_list_loader(self, only_last_index = False):
        with open(self.path, 'rb') as file:
            objs = []
            while True:
                try:
                    objs.append(pickle.load(file))
                except EOFError as e:
                    break
        if only_last:
            return objs[-1]["user_id"]
        else:
            return objs
        
    
    def get_tweets(self, app, user_id, oldest):
        tweets = []
        try:
            if oldest is None:
                itr = tweepy.Cursor(app.user_timeline, user_id= user_id).items()
            else:
                itr = tweepy.Cursor(app.user_timeline, user_id= user_id, max_id = oldest).items()

            for tweet in itr:
                tweets.append(tweet)
    
        except:
            pass
        return tweets


                
    def run(self):
        #apps = self.apps
        n = 0
        #mode = "user"
        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
        appFail = False
        i = 0
        to_be_written = []
        all_used = False
        index = 0
        if os.path.exists(self.path) and self.restart:
            try:
                last_id  = self.followers_loader(only_last = True)
                #last_id = already_downloaded_objs[-1][0]
                #print("last_id = ",last_id )
                index = np.where(self.ids == last_id)[0][0] + 1
                all_used = True
            except _pickle.UnpicklingError as e:
                print(self.name, ": File",self.path, " corrupted, delete that file. The thread will start from index = 0 writing in a new file called",self.path[:-4] + "_new.txt \n")
                index = 0 
                self.path = self.path[:-4] + "_new.txt"
            
        total = len(self.ids[index:])
        print(self.name,"started. Downloading user objects from user_id",self.ids[index], "to",self.ids[-1],"so we start from index",index,"\n")
        
        for user_id in self.ids[index:]:
            #cursor = -1
            
            #fllwrs = []
            user_favorited_count = 0
            user_retweeted_count = 0
            
            tweets_ids = []
            
            retweeted_users_ids = []
            retweeted_tweets_ids = []
            mentioned_users_ids = []
            tweets  = []
            oldest = None
            new_tweets  = []
            hashtags = []
            
            terminate = False
            last_date = datetime.now()
            while True:
                try:
                    
                    failed  = False
                    
                    while len(new_tweets) > 0 or oldest is None and last_date > self.target_date :
                        new_tweets = []
                        new_tweets.extend(self.get_tweets(app =app, user_id = user_id, oldest = oldest))
                        if len(new_tweets) > 0:
                            tweets.extend(new_tweets)
                            oldest = new_tweets[-1].id -1
                            last_date = new_tweets[-1].created_at
                        else:
                            break
                                

                    for tweet in tweets:
                        try:
                            
                            tweets_ids.append(tweet.id)
                            
                            user_favorited_count += tweet.favorite_count
                            user_retweeted_count += tweet.retweet_count
                            hashtags.extend([dct["text"] for dct in tweet.entities["hashtags"]]) #we proved that it also takes retweets' hashtags
                            mentioned_users_ids.extend([mention["id"] for mention in tweet.entities["user_mentions"]])
                            retweeted_status = tweet.retweeted_status
                            #hashtags.append(retweeted_status.entities["hashtags"]) 
                            retweeted_users_ids.append(retweeted_status.user.id)
                            retweeted_tweets_ids.append(retweeted_status.id)
                            
                        except AttributeError:
                            continue
                                
                    
                    #hashtags = [dct["text"] for lst in hashtags for dct in lst]
                                
                    CE_times = 0
                            


                except tweepy.RateLimitError:
#                     if len(to_be_written) >0:
#                         with open(self.path, "ab") as f: # see https://stackoverflow.com/questions/36965507/writing-a-dictionary-to-a-text-file
#                             pickle.dump(to_be_written, f) # f.write(pickle.dumps(dct)) json.dumps(user). Actually saving it as a string or serialized is equally slow
#                             to_be_written = []
                            #print(self.name,":written up to",i,"-th user whose id is ",user_id)
                    if not appFail : #mode == "user" and
                        #print("App number",n,"with user auth depleted, authenticationg as app...")
                        self.mode  = "app"
                        app = self.logger(self.apps[n],mode = self.mode,wait_on_rate_limit = False)
                        remaining = self.get_limits(app,path = self.resource_remaining)
                        #print("remaining = ", remaining)
                        if remaining == 0 and all_used:
                            wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                            if self.name == "thread1":
                                print(self.name,";sleeping", wait + 10, " seconds to ensure timers are reset...", end = "\n")
                            time.sleep(wait + 10)
                        appFail = True
                        continue
                    else:
                        self.mode  = "user"
                        #print(self.name,"Also app auth of",n,"-th app has been depleted. Switching to next app...")
                        if n == len(self.apps)-1:
                            #if self.name == "thread1":
                                #print("last app was actually depleted. Restarting from n = 0....",end = "\r")
                            n = 0
                            all_used = True
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,path = self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0:
                                wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                if self.name == "thread1":
                                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                time.sleep(wait + 10)
                        else:
                            n = n+1
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,path = self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0 and all_used:
                                wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                if self.name == "thread1":
                                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                time.sleep(wait + 10)
                        appFail = False
                        continue
                except tweepy.TweepError as e:
                    #if e.api_code == 50: #https://stackoverflow.com/a/48499300 #https://www.programcreek.com/python/?code=SMAPPNYU%2FsmappPy%2FsmappPy-master%2FsmappPy%2Ftweepy_pool.py#   #https://github.com/tweepy/tweepy/issues/1254
                        i = i+1
                        failed = True
#                         if self.name == "thread1":
                        #print("User",user_id,"not found, skipping...")
                        break
                except ConnectionError as e:
                    if CE_times < 5:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,"\nRelogging the app number",n," for the",CE_times,"time.\n ")
                        time.sleep(5)
                        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                        CE_times += 1
                        continue
                    else:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,". Tried to reconnect for 5 times in a row without success. The user_id during which the exception occured was",user_id,". Exiting...")
                        terminate = True
                        break
                except Exception as e:
                    print(self.name,": Exception occurred at user", user_id,"with app number",n)
                    failed = True
                    raise e
                if not failed:
                    to_be_written = {"user_id":user_id,"user_favorited_count": user_favorited_count, "user_retweeted_count":user_retweeted_count, "retweeted_users_ids":retweeted_users_ids,"retweeted_tweets_ids":retweeted_tweets_ids, "hashtags":hashtags ,"mentioned_users_ids":mentioned_users_ids,"tweets_ids":tweets_ids }#dct
                    #news = np.array([fllwr for fllwr in fllwrs if fllwr not in self.all_downloaded])
                    #print("len(fllwrs) = ",len(fllwrs),"\n" )
                    #print("len(self.all_downloaded) = ",len(self.all_downloaded),"\n" )
                    #print("len(news) = ", len(news),"\n")
                    #self.all_downloaded = np.concatenate((self.all_downloaded,news))
                    #self.all_downloaded_jumped = np.concatenate((self.all_downloaded_jumped,news))
                    with open(self.path, "ab") as f: # see https://stackoverflow.com/questions/36965507/writing-a-dictionary-to-a-text-file
                        f.write(pickle.dumps(to_be_written)) # f.write(pickle.dumps(dct)) json.dumps(user). Actually saving it as a string or serialized is equally slow


                i = i+1
                if self.name == "thread1":
                    print(self.name,": downloaded ",i," retweets sets out of",total,"total. Currently using with app number",n,"and the last user_id was",user_id,end = "\r") 
                break

            # if for 5 times (spaced bt 5 seconds) teh app couldent reconnect follwing a ConnectionError exception, terminate the thread            
            if terminate:
                break
            
        print(self.name,"FINISHED!!! \n")
        
        
        
        
        
class TwitterThreadFVRT(Thread):
    
    #printer = Printer(2)
    
    def __init__(self,name,apps,ids,path,resource_remaining,resource_reset, restart = False): #here
        Thread.__init__(self)
        self.name = name
        self.apps = apps
        self.ids = ids
        self.path = path
        self.restart = restart
        self.resource_remaining = resource_remaining
        self.resource_reset = resource_reset
        
        self.mode  = "user"
    
    def utc_s(self): #https://stackoverflow.com/questions/5998245/get-current-time-in-milliseconds-in-python
        return round(datetime.utcnow().timestamp()) + (60*60*2)

    def logger(self,credentials,mode, wait_on_rate_limit = True):
        total = len(self.ids)
        retry_count = 1
        retry_delay = 5
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")

    # Fields of user object that we may use to estimate activity: location':"", 'profile_location'=None, 'protected':False,'followers_count': 17,'friends_count': 197,'created_at': 'Sat Sep 28 23:13:30 +0000 2019', 'favourites_count': 28,'statuses_count': 1,follow_request_sent=False

    def get_limits(self,app,path = None):
        limits = app.rate_limit_status()
        if path is not None:
            limit = limits
            for branch in path: 
                limit = limit[branch]
            return limit
        else:
            return limits
        
        
    def test(self,mode = "user",screen_name = "ClaudioMoroni3"):
        i = 0
        apps = self.logger(self.apps, mode = mode ,wait_on_rate_limit = False)
        for app in apps:
            try:
                user = app.get_user(screen_name = screen_name)
                print("app number",i,"authentication succeded")
                i +=1
            except tweepy.TweepError as e:
                print("app number",i,"authentication failed, with reason:", e.response.text)
                i +=1

    # loads and returns user-followers list of type [[user1,[user1_follower1,user1_follower2,...]],[user2,[user2_follower1,user2_follower2,...]],...]
    def followers_loader(self): #inspired by rw_to_TwitterThread
        with open(self.path, "rb") as f:
            rw_ids_raw = []
            while 1:
                try:
                    rw_ids_raw.append(pickle.load(f))
                except EOFError:
                    break
            f.close()
        return np.array(rw_ids_raw)
    
    
    def dct_list_loader(self, only_last_index = False):
        with open(self.path, 'rb') as file:
            objs = []
            while True:
                try:
                    objs.append(pickle.load(file))
                except EOFError as e:
                    break
        if only_last:
            return objs[-1]["user_id"]
        else:
            return objs
        
    
    def get_tweets(self, app, user_id, oldest):
        tweets = []
        try:
            if oldest is None:
                itr = tweepy.Cursor(app.user_timeline, user_id= user_id).items()
            else:
                itr = tweepy.Cursor(app.user_timeline, user_id= user_id, max_id = oldest).items()

            for tweet in itr:
                tweets.append(tweet)
    
        except:
            pass
        return tweets


                
    def run(self):
        #apps = self.apps
        n = 0
        #mode = "user"
        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
        appFail = False
        i = 0
        to_be_written = []
        all_used = False
        index = 0
        if os.path.exists(self.path) and self.restart:
            try:
                last_id  = self.followers_loader(only_last = True)
                #last_id = already_downloaded_objs[-1][0]
                #print("last_id = ",last_id )
                index = np.where(self.ids == last_id)[0][0] + 1
                all_used = True
            except _pickle.UnpicklingError as e:
                print(self.name, ": File",self.path, " corrupted, delete that file. The thread will start from index = 0 writing in a new file called",self.path[:-4] + "_new.txt \n")
                index = 0 
                self.path = self.path[:-4] + "_new.txt"
            
        total = len(self.ids[index:])
        print(self.name,"started. Downloading user objects from user_id",self.ids[index], "to",self.ids[-1],"so we start from index",index,"\n")
        
        for user_id in self.ids[index:]:
            #cursor = -1
            
            #fllwrs = []
            favorited_users_ids = []
            favorites  = []
            page = 0
            new_favorites  = []
            favorited_tweets_ids = []
            hashtags = []
            terminate = False
            mentioned_users_ids = []
            while True:
                try:
                    
                    failed  = False
                    
                    while len(new_favorites) > 0 or page == 0 or failed: #or oldest is None:
                        
                        new_favorites =app.favorites(user_id=user_id, page = page)
                        #new_tweets.extend(self.get_tweets(app =app, user_id = user_id, oldest = oldest))
                        
                        if len(new_favorites) > 0:
                            favorites.extend(new_favorites)
                            page += 1
                        else:
                            break
                                

                    for favorite in favorites:
                        
                        favorited_users_ids.append(favorite.user.id)
                        favorited_tweets_ids.append(favorite.id)
                        hashtags.append(favorite.entities["hashtags"]) 
                        mentioned_users_ids.extend([mention["id"] for mention in favorite.entities["user_mentions"]])
                    
                    hashtags = [dct["text"] for lst in hashtags for dct in lst]
                                
                    CE_times = 0
                            
                    

                except tweepy.RateLimitError:
#                     if len(to_be_written) >0:
#                         with open(self.path, "ab") as f: # see https://stackoverflow.com/questions/36965507/writing-a-dictionary-to-a-text-file
#                             pickle.dump(to_be_written, f) # f.write(pickle.dumps(dct)) json.dumps(user). Actually saving it as a string or serialized is equally slow
#                             to_be_written = []
                            #print(self.name,":written up to",i,"-th user whose id is ",user_id)
                    if not appFail : #mode == "user" and
                        #print("App number",n,"with user auth depleted, authenticationg as app...")
                        self.mode  = "app"
                        app = self.logger(self.apps[n],mode = self.mode,wait_on_rate_limit = False)
                        remaining = self.get_limits(app,path = self.resource_remaining)
                        #print("remaining = ", remaining)
                        if remaining == 0 and all_used:
                            wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                            if self.name == "thread1":
                                print(self.name,";sleeping", wait + 10, " seconds to ensure timers are reset...", end = "\n")
                            time.sleep(wait + 10)
                        appFail = True
                        continue
                    else:
                        self.mode  = "user"
                        #print(self.name,"Also app auth of",n,"-th app has been depleted. Switching to next app...")
                        if n == len(self.apps)-1:
                            #if self.name == "thread1":
                                #print("last app was actually depleted. Restarting from n = 0....",end = "\r")
                            n = 0
                            all_used = True
                            app = self.logger(self.apps[n], mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,path = self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0:
                                wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                if self.name == "thread1":
                                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                time.sleep(wait + 10)
                        else:
                            n = n+1
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,path = self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0 and all_used:
                                wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                if self.name == "thread1":
                                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                time.sleep(wait + 10)
                        appFail = False
                        continue
                except tweepy.TweepError as e:
                    #if e.api_code == 50: #https://stackoverflow.com/a/48499300 #https://www.programcreek.com/python/?code=SMAPPNYU%2FsmappPy%2FsmappPy-master%2FsmappPy%2Ftweepy_pool.py#   #https://github.com/tweepy/tweepy/issues/1254
                        i = i+1
                        failed = True
#                         if self.name == "thread1":
                        #print("User",user_id,"not found, skipping...")
                        break
                except ConnectionError as e:
                    if CE_times < 5:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,"\nRelogging the app number",n," for the",CE_times,"time.\n ")
                        time.sleep(5)
                        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                        CE_times += 1
                        continue
                    else:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,". Tried to reconnect for 5 times in a row without success. The user_id during which the exception occured was",user_id,". Exiting...")
                        terminate = True
                        break
                except Exception as e:
                    print(self.name,": Exception occurred at user", user_id,"with app number",n)
                    failed = True
                    raise e
                if not failed:
                    to_be_written = {"user_id":user_id,"favorited_users_ids": favorited_users_ids, "favorited_tweets_ids":favorited_tweets_ids, "hashtags":hashtags, "mentioned_users_ids":mentioned_users_ids}#dct
                    #news = np.array([fllwr for fllwr in fllwrs if fllwr not in self.all_downloaded])
                    #print("len(fllwrs) = ",len(fllwrs),"\n" )
                    #print("len(self.all_downloaded) = ",len(self.all_downloaded),"\n" )
                    #print("len(news) = ", len(news),"\n")
                    #self.all_downloaded = np.concatenate((self.all_downloaded,news))
                    #self.all_downloaded_jumped = np.concatenate((self.all_downloaded_jumped,news))
                    with open(self.path, "ab") as f: # see https://stackoverflow.com/questions/36965507/writing-a-dictionary-to-a-text-file
                        f.write(pickle.dumps(to_be_written)) # f.write(pickle.dumps(dct)) json.dumps(user). Actually saving it as a string or serialized is equally slow


                i = i+1
                if self.name == "thread1":
                    print(self.name,": downloaded ",i," favorites sets out of",total,"total. Currently using with app number",n,"and the last user_id was",user_id,end = "\r") 
                break

            # if for 5 times (spaced bt 5 seconds) the app couldn't reconnect following a ConnectionError exception, terminate the thread            
            if terminate:
                break
            
        print(self.name,"FINISHED!!! \n")
        
        
        
        
        
        
        
        
    



class TwitterThreadMonitor(Thread):
    
    #printer = Printer(2)
    
    def __init__(self,name,apps,path,backup_path,objs_save_path ,objs_backup_path, hashtags_path,hashtags_backup_path,mentions_path, mentions_backup_path, save_every,objs  = None, restart = False): #here
        Thread.__init__(self)
        self.name = name
        self.apps = apps
        #self.objs = objs
        self.save_every = save_every
        
        self.path = path
        self.backup_path = backup_path
        self.objs_save_path = objs_save_path
        self.objs_backup_path = objs_backup_path
        self.hashtags_path = hashtags_path
        self.hashtags_backup_path = hashtags_backup_path
        self.mentions_path = mentions_path
        self.mentions_backup_path = mentions_backup_path
        
        if restart:
            if self.name == "thread0":
                print("restart request detected, loading previous objects...")
            try:
                self.objs = np.load(self.objs_save_path, allow_pickle = True)
                print(self.name,"; objects correctly loaded")
            except _pickle.UnpicklingError as e:
                print(self.name,"; main objects file corrupted, trying with backup...")
                try:
                    self.objs = np.load(self.objs_backup_path, allow_pickle = True)
                    print(self.name,"; backup objects correctly loaded")
                except _pickle.UnpicklingError as e:
                    print(self.name, "; also backup is corrupted, loading initial objects...")
                    self.objs = objs
                    print(self.name, "; done")
                    
        else:
            self.objs = objs
            
        # ids over which to iterate in the main for loop of the run method
        self.ids = np.array([obj["user_id"] for obj in self.objs])
        #self.restart = restart # is it needed?
        self.remaining_user = ["resources","users","/users/:id","remaining"]
        self.reset_user = ["resources","users","/users/:id","reset"]
        
        self.remaining_followers = ["resources","followers",'/followers/ids',"remaining"]
        self.reset_followers = ["resources","followers",'/followers/ids',"reset"]
        
        self.remaining_retweets = ["resources","statuses",'/statuses/user_timeline',"remaining"]
        self.reset_retweets = ["resources","statuses",'/statuses/user_timeline',"reset"]
        
        self.remaining_favorites = ["resources","favorites","/favorites/list","remaining"]
        self.reset_favorites = ["resources","favorites","/favorites/list","reset"]
        
        self.mode  = "user"
    
    def utc_s(self): #https://stackoverflow.com/questions/5998245/get-current-time-in-milliseconds-in-python
        return round(datetime.utcnow().timestamp()) + (60*60*2)

    def logger(self,credentials,mode, wait_on_rate_limit = True):
        total = len(self.ids)
        retry_count = 2
        retry_delay = 5
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")

    # Fields of user object that we may use to estimate activity: location':"", 'profile_location'=None, 'protected':False,'followers_count': 17,'friends_count': 197,'created_at': 'Sat Sep 28 23:13:30 +0000 2019', 'favourites_count': 28,'statuses_count': 1,follow_request_sent=False

    def get_limits(self,app,path = None):
        limits = app.rate_limit_status()
        if path is not None:
            limit = limits
            for branch in path: 
                limit = limit[branch]
            return limit
        else:
            return limits
        
        
    def test(self,mode = "user",screen_name = "ClaudioMoroni3"):
        i = 0
        apps = self.logger(self.apps, mode = mode ,wait_on_rate_limit = False)
        for app in apps:
            try:
                user = app.get_user(screen_name = screen_name)
                #print("app number",i,"authentication succeded")
                i +=1
            except tweepy.TweepError as e:
                #print("app number",i,"authentication failed, with reason:", e.response.text)
                i +=1


    def loader(self,path):
        with open(path, "rb") as f:
            objs = []
            while 1:
                try:
                    objs.append(pickle.load(f))
                except EOFError:
                    break
            f.close()

        #objs = [x for y in objs for x in y]
        #print(len(objs))


        return np.array(objs)
    
#     def append_list_as_row(self,file_name, list_of_elem):
#         # Open file in append mode
#         with open(file_name, 'a+', newline='') as write_obj:
#             # Create a writer object from csv module
#             csv_writer = writer(write_obj)
#             # Add contents of list as last row in the csv file
#             csv_writer.writerow(list_of_elem)
            
#     def find_last_index(self,elem, old_reversed,already,Min):
#         #old_reversed = old[::-1]
#         for i in zip(list(range(len(old_reversed))),old_reversed):
#             if i[1]==elem and i[0] not in already:
#                 if len(old_reversed)-i[0]-1 < Min:
#                     already.append(i[0])

#                     return len(old_reversed)-i[0]-1
#                     break
    
    def list_compare(self,new,old, mode):
        added = []
        removed = []
        if mode == "follower":
            new_followers_ids = set(new["followers_ids"])
            old_followers_ids = set(old["followers_ids"])

            added = list(new_followers_ids.difference(old_followers_ids))

            try:
                last_follower_id = new["followers_ids"][-1]
                last_follower_id_index_in_old = old["followers_ids"].index(last_follower_id)
            except ValueError:
                added = new["followers_ids"]
                last_follower_id_index_in_old = 0               
            except IndexError:
                added = []
                last_follower_id_index_in_old = 0

            old_followers_ids_trunc_set = set(old["followers_ids"][:last_follower_id_index_in_old+1])


            removed = list(old_followers_ids_trunc_set.difference(new_followers_ids))  #[tweet_id for tweet_id in new_retweeted_tweets_ids if tweet_id not in 

            old["followers_ids"] = added + old["followers_ids"]

            for rem in removed:
                old["followers_ids"].remove(rem)

            return ({"added":added,"removed":removed},old)

        else:

            if mode == "retweet":
                tweets_ids = "retweeted_tweets_ids"
                users_ids = "retweeted_users_ids"
            elif mode == "favorite":
                tweets_ids = "favorited_tweets_ids"
                users_ids = "favorited_users_ids"

        #     added = []
        #     removed = []
            #added_tweets_ids_indices = []

            new_retweeted_tweets_ids = set(new[tweets_ids])
            old_retweeted_tweets_ids = set(old[tweets_ids])

            added_tweets_ids = new_retweeted_tweets_ids.difference(old_retweeted_tweets_ids) #[tweet_id for tweet_id in new_retweeted_tweets_ids if tweet_id not in old_retweeted_tweets_ids ]
            #print("0")
            for Id in added_tweets_ids:
                added.append(new[users_ids][new[tweets_ids].index(Id)])

            try:
                last_retweed_id = new[tweets_ids][-1]
                last_retweet_id_index_in_old = old[tweets_ids].index(last_retweed_id )
            except ValueError:
                added = new[users_ids]
                last_retweet_id_index_in_old = 0   
            except IndexError:
                added = []
                last_retweet_id_index_in_old = 0
                
            #print("1")
            old_retweeted_tweets_ids_trunc_set = set(old[tweets_ids][:last_retweet_id_index_in_old+1])
            #print("2")
            removed_tweets_ids = old_retweeted_tweets_ids_trunc_set.difference(new_retweeted_tweets_ids)  #[tweet_id for tweet_id in new_retweeted_tweets_ids if tweet_id not in old_retweeted_tweets_ids ]
            #print("3")
            for Id in removed_tweets_ids:
                removed.append(old[users_ids][old[tweets_ids].index(Id)])


            #shift  = len(added)-len(removed)
            #print("4")
            old[users_ids] = added + old[users_ids]
            #print("5")
            old[tweets_ids] = list(added_tweets_ids) + old[tweets_ids]
            #print("6")
            for rem in removed:
                old[users_ids].remove(rem)
            
            #print("7")
            for rem in removed_tweets_ids:
                old[tweets_ids].remove(rem) 


            #print("8")
            return ({"added":added,"removed":removed},old)
        
        
    def handle_rateLimit(self,name,n,remaining, reset, appFail, all_used):
        #print("\n relogging name ")
        if not appFail : #mode == "user" and
            #print("\n relogging", name, "number",n,"as app")
            #print("App number",n,"with user auth depleted, authenticationg as app...")
            self.mode  = "app"
            app = self.logger(self.apps[n],mode = self.mode,wait_on_rate_limit = False)
            remaining = self.get_limits(app,path = remaining)
            #print("remaining = ", remaining)
            if remaining == 0 and all_used:
                wait = self.get_limits(app,path = reset) - self.utc_s()
                #if self.name == "thread1":
                print(self.name,";sleeping", wait + 10, " seconds to ensure timers are reset...", end = "\n")
                time.sleep(wait + 10)
            appFail = True
            #continue
            return (app,n,appFail,all_used)
        else:
            
            self.mode  = "user"
            #print(self.name,"Also app auth of",n,"-th app has been depleted. Switching to next app...")
            if n == len(self.apps)-1:
               # print("\n relogging", name, "number",0,"as user")
                #if self.name == "thread1":
                    #print("last app was actually depleted. Restarting from n = 0....",end = "\r")
                n = 0
                all_used = True
                app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                remaining = self.get_limits(app,path = remaining)
                #print("remaining = ", remaining)
                if remaining == 0:
                    wait = self.get_limits(app,path = reset) - self.utc_s()
                    #if self.name == "thread1":
                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                    time.sleep(wait + 10)
            else:
                n = n+1
                #print("\n relogging", name, "number",n,"as user")
                app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                remaining = self.get_limits(app,path = remaining)
                #print("remaining = ", remaining)
                if remaining == 0 and all_used:
                    wait = self.get_limits(app,path = reset) - self.utc_s()
                    #if self.name == "thread1":
                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                    time.sleep(wait + 10)
            appFail = False
            #print("returning logged app")
            return (app,n,appFail,all_used)
    
    
    
                
    def run(self):
        #apps = self.apps
        n_user = 0
        n_followers = 0
        n_retweets = 0
        n_favorites = 0
        
        user_app = self.logger(self.apps[n_user],mode = self.mode, wait_on_rate_limit = False)
        followers_app = self.logger(self.apps[n_followers],mode = self.mode, wait_on_rate_limit = False)
        retweets_app = self.logger(self.apps[n_retweets],mode = self.mode, wait_on_rate_limit = False)
        favorites_app = self.logger(self.apps[n_favorites],mode = self.mode, wait_on_rate_limit = False)
        
        appFail_user = False
        appFail_followers = False
        appFail_retweets = False
        appFail_favorites = False
        
        #to_be_written = []
        all_used = False
        index = 0
            
        total = len(self.ids[index:])
        total_lines = 0
        print(self.name,"started. Monitoring user objects from user_id",self.ids[0], "to",self.ids[-1],"so we start from index",index,"\n")
        iteration = 0
        lines =[]
        hashtags = []
        mentions = []
        while True:
            i = 0
            iteration  += 1
            for obj in self.objs:
                started = False
                user_id = obj["user_id"]
                fllwrs = []
                terminate = False
                
                got_user = False
                got_followers = False
                got_retweets = False
                got_favorites  = False
                
                tweets_ids = []
                retweeted_users_ids = []
                retweeted_tweets_ids = []
                current_hashtags = []
                current_mentions = []
                
                favorited_users_ids = []
                favorited_tweets_ids = []
                
                Time = self.utc_s()
                CE_times = 0
                #lines = []
                while True:
                    failed = False
                    try:
                        
                        if not got_user:
                            user = user_app.get_user(user_id = obj["user_id"])
                            dct = {"followers_difference":obj["followers_count"]-user.followers_count,"statuses_difference":obj["statuses_count"]-user.statuses_count,"favorites_difference":obj["favourites_count"]-user.favourites_count}
                            obj["followers_count"] = user.followers_count
                            obj["statuses_count"] = user.statuses_count
                            obj["favourites_count"] = user.favourites_count
                            got_user = True
                        
                        
                        if not got_followers:
                            if dct["followers_difference"] != 0:
                                print("getting followers", end = "\r")
                                #followers_failed = True
                                followers = followers_app.followers_ids(user_id=user_id) # this will give the most recent 5000 follwers ids
                                new = {"followers_ids":followers}
                                added_removed_followers,obj = self.list_compare(new, obj, mode ="follower")
                                started = True
                            else:
                                added_removed_followers = {"added":[], "removed":[]}
                            
                            # do something
                            

                            #followers_failed = False
                            got_followers = True
                        if not got_retweets:
                            if dct["statuses_difference"] != 0:
                                #print("getting retweets", end = "\n")
                                #retweets_failed = True
                                tweets_curs = tweepy.Cursor(retweets_app.user_timeline,user_id = user_id).items(40) # this will give the most recent 40 statuses. Since a page returned by app.user_timeline consists of 20 tweets, this line will consume 2 calls 
                                tweets = [tweet for tweet in tweets_curs]
                                #current_hashtags =[]
                                for tweet in tweets:
                                    try:
                                        #print("getting hashtags...")
                                        tweets_ids.append(tweet.id)
                                        current_hashtags.append({"tweet_id":tweet.id, "hashtags":tuple(dct["text"] for dct in tweet.entities["hashtags"])}) #current_hashtags.append(tuple(dct["text"] for dct in tweet.entities["hashtags"]))
                                        
                                        current_mentions.append({"tweet_id":tweet.id, "mentioned_users_ids":tuple(mention["id"] for mention in tweet.entities["user_mentions"])})
                                        #obj["hashtags"]  = tweet.entities["hashtags"] + obj["hashtags"]
                                        #print("getting retweeted tweets")
                                        retweeted_status = tweet.retweeted_status
                                        #print("1")
                                        retweeted_users_ids.append(retweeted_status.user.id)
                                        #print("2")
                                        retweeted_tweets_ids.append(retweeted_status.id)
                                        #print("got_retweets")
                                    except AttributeError:
                                        continue

                                #hashtags.append((obj["user_id"],current_hashtags,time,iteration))
                                new = {"retweeted_users_ids":retweeted_users_ids,"retweeted_tweets_ids":retweeted_tweets_ids}
                                new_tweets = set(tweets_ids) - set(obj["tweets_ids"]) 
                                added_removed_retweets, obj = self.list_compare(new, obj,mode ="retweet")
                                
                                hashtags.append((obj["user_id"],[hashtag_obj["hashtags"] for hashtag_obj in current_hashtags if hashtag_obj["tweet_id"] in new_tweets],Time,iteration))
                                mentions.append((obj["user_id"],[mention_obj["mentioned_users_ids"] for mention_obj in current_mentions if mention_obj["tweet_id"] in new_tweets],Time,iteration))
                                new_tweets_without_retweets = list(new_tweets - set(added_removed_retweets["added"]))
                                obj["tweets_ids"] = new_tweets_without_retweets + obj["tweets_ids"]
                                tweets_ids = []
                                current_hashtags = []
                                current_mentions = []
                                started = True
                                #print("added_removed_rewteets = ",added_removed_retweets)
                            else:
                                added_removed_retweets = {"added":[], "removed":[]}
                                

                            #retweets_failed = False
                            # do something
                            got_retweets = True
                            
                        if not got_favorites: #https://www.geeksforgeeks.org/python-api-favorites-in-tweepy/
                            if dct["favorites_difference"] != 0:
                                print("getting favorites", end = "\r")
                                #favorites_failed = True
                                favorited_tweets_curs = tweepy.Cursor(favorites_app.favorites, user_id = user_id).items(60)  ## this will give the most recent 40 favorited statuses. Since a page returned by app.favorites consists of 20 tweets, this line will consume 3 calls (limit is 75 calls, so if we take only 40 we would have a RateLimitException in between an iteration, and we don't really want it.Plus favorites are more frequent than retweets)
                                favorited_tweets = [tweet for tweet in favorited_tweets_curs]
                                for favorite in favorited_tweets:
                                    tweets_ids.append(favorite.id)
                                    current_hashtags.append({"tweet_id":favorite.id, "hashtags":tuple(dct["text"] for dct in favorite.entities["hashtags"])}) #current_hashtags.append(tuple(dct["text"] for dct in tweet.entities["hashtags"]))
                                        
                                    current_mentions.append({"tweet_id":favorite.id, "mentioned_users_ids":tuple(mention["id"] for mention in favorite.entities["user_mentions"])})
                                    favorited_users_ids.append(favorite.user.id)
                                    favorited_tweets_ids.append(favorite.id)


                                # do something
                                new = {"favorited_users_ids":favorited_users_ids, "favorited_tweets_ids":favorited_tweets_ids} 
                                new_favorites = set(tweets_ids) - set(obj["favorited_tweets_ids"]) 
                                added_removed_favorites,obj =  self.list_compare(new, obj,mode ="favorite")
                                hashtags.append((obj["user_id"],[hashtag_obj["hashtags"] for hashtag_obj in current_hashtags if hashtag_obj["tweet_id"] in new_favorites],Time,iteration))
                                mentions.append((obj["user_id"],[mention_obj["mentioned_users_ids"] for mention_obj in current_mentions if mention_obj["tweet_id"] in new_favorites],Time,iteration))
                                tweets_ids = []
                                current_hashtags = []
                                current_mentions = []
                                started = True
                            #favorites_failed = False
                            else:
                                added_removed_favorites = {"added":[], "removed":[]}
                                
                            got_favorites = True
                            
                        
                        CE_times = 0
                        i = i+1
                        break
                    except tweepy.RateLimitError:
                        
                        if not got_user:
                            user_app,n_user, appFail_user,all_used = self.handle_rateLimit(name = "user_app",n = n_user,remaining = self.remaining_user, reset = self.reset_user, appFail =appFail_user, all_used = all_used)

                        if not got_followers:
                            followers_app,n_followers, appFail_followers,all_used = self.handle_rateLimit(name = "followers_app",n = n_followers,remaining = self.remaining_followers, reset = self.reset_followers, appFail =appFail_followers, all_used = all_used)
                            
                        elif not got_retweets:
                            retweets_app,n_retweets, appFail_retweets,all_used = self.handle_rateLimit(name = "retweets_app",n = n_retweets,remaining = self.remaining_retweets, reset = self.reset_retweets, appFail =appFail_retweets, all_used = all_used)
#                         elif not got_favorites:
#                             favorites_app,n_favorites, appFail,all_used = self.handle_rateLimit(name = "favorites_app",n = n_favorites,remaining = self.remaining_favorites, reset = self.reset_favorites, appFail =appFail, all_used = all_used)
                        continue
                    except ConnectionResetError as e: #ConnnectionError
                        if CE_times < 5:
                            print("Caught a  ConnectionError, with reason:\n", e.reason,"\nRelogging the app number",n," for the",CE_times,"time.\n ")
                            time.sleep(5)
                            if not got_followers:
                                followers_app = self.logger(self.apps[n_followers],mode = self.mode, wait_on_rate_limit = False)
                                
                            if not got_retweets:
                                retweets_app = self.logger(self.apps[n_retweets],mode = self.mode, wait_on_rate_limit = False)
                                
                            if not got_favorites:
                                favorites_app = self.logger(self.apps[n_favorites],mode = self.mode, wait_on_rate_limit = False)
                            CE_times += 1
                            continue
                        else:
                            print("Caught a  ConnectionError, with reason:\n", e.reason,". Tried to reconnect for 5 times in a row without success. The user_id during which the exception occured was",user_id,". Exiting...")
                            terminate = True
                            break
                    except tweepy.TweepError as e:
                        if e.reason == 'Twitter error response: status code = 429': #https://stackoverflow.com/a/48499300 #https://www.programcreek.com/python/?code=SMAPPNYU%2FsmappPy%2FsmappPy-master%2FsmappPy%2Ftweepy_pool.py#   #https://github.com/tweepy/tweepy/issues/1254
                            print("error 429, relogging...", end = "\r")
                            favorites_app,n_favorites, appFail_favorites,all_used = self.handle_rateLimit(name =  "favorites_app",n = n_favorites,remaining = self.remaining_favorites, reset = self.reset_favorites, appFail =appFail_favorites, all_used = all_used)
                            continue
                        elif "Failed to send request" in e.reason:
                            print("caught unknown tweepError for user",user_id,":",e.__dict__,"reconnecting...", end = "\r") #e.response.text #tweepy.error.TweepError: Failed to send request: ('Connection aborted.', ConnectionResetError(10054, "Connessione in corso interrotta forzatamente dall'host remoto", None, 10054, None))
                            if CE_times < 5:
                                print("Caught a  ConnectionError, with reason:", e.reason,"Relogging the apps numbers: n_user = ", n_user,"n_followers = ",n_followers,"n_retweets = ",n_retweets,"n_favorites = ",n_favorites  ,"for the",CE_times,"time.\n ")
                                time.sleep(5)
                                if not got_followers:
                                    followers_app = self.logger(self.apps[n_followers],mode = self.mode, wait_on_rate_limit = False)

                                if not got_retweets:
                                    retweets_app = self.logger(self.apps[n_retweets],mode = self.mode, wait_on_rate_limit = False)

                                if not got_favorites:
                                    favorites_app = self.logger(self.apps[n_favorites],mode = self.mode, wait_on_rate_limit = False)
                                CE_times += 1
                                continue
                            else:
                                print("Caught a  ConnectionError, with reason:\n", e.reason,". Tried to reconnect for 5 times in a row without success. The user_id during which the exception occured was",user_id,". Exiting...")
                                terminate = True
                                break    
                        else:
                            print("caught unknown tweepError for user",user_id,":",e.__dict__,"skipping...")
                            i = i+1
                            failed = True
    #                         if self.name == "thread1":

                            #print("User",user_id,"not found, skipping...")
                            #raise e
                            break
                    except Exception as e:
                        print(self.name,": Exception occurred at user", user_id,"e.__dict__ = ",e.__dict__)
                        failed = True
                        raise e
                if not failed and started:
                    
                    
                    lines.extend(tuple((obj["user_id"],target,"follow",Time, iteration) for target in added_removed_followers["added"]))
                    lines.extend(tuple((obj["user_id"],target,"unfollow",Time,iteration) for target in added_removed_followers["removed"]))   
                    lines.extend(tuple((obj["user_id"],target,"retweet",Time,iteration) for target in added_removed_retweets["added"]))
                    lines.extend(tuple((obj["user_id"],target,"unretweet",Time,iteration) for target in added_removed_retweets["removed"]))
                    lines.extend(tuple((obj["user_id"],target,"favorite",Time,iteration) for target in added_removed_favorites["added"]))
                    lines.extend(tuple((obj["user_id"],target,"unfavorite",Time,iteration) for target in added_removed_favorites["removed"]))
                    
                    total_lines += len(lines)
                    started = False
                    
                    #hashtags.append((obj["user_id"],current_hashtags,time,iteration))
                    
                    #for line in lines:
                        
                    
                    # save as csv
#                     for line in lines:
#                         self.append_list_as_row(self.path+".csv", line)

#                     with open(self.path+".csv") as f:
#                         my_reader = reader(f)
#                         lines= len(list(my_reader))
                    #end of save as csv
    
                    # save as pickle
                
                if i%self.save_every == 0:
                    if self.name == "thread0":
                        print("saving and backupping...", end = "\r")

#                 if i%self.save_every == 0:
                    with open(self.path, "ab") as f:
                        pickle.dump(lines,f)

                    with open(self.hashtags_path, "ab") as f:
                        pickle.dump(hashtags,f)
                        
                    with open(self.mentions_path, "ab") as f:
                        pickle.dump(mentions,f)    
                        

                    with open(self.backup_path, "ab") as f:
                        pickle.dump(lines,f)

                    with open(self.hashtags_backup_path, "ab") as f:
                        pickle.dump(hashtags,f)
                        
                        
                    with open(self.mentions_backup_path, "ab") as f:
                        pickle.dump(mentions,f)

                    np.save(self.objs_save_path,self.objs)
                    np.save(self.objs_backup_path, self.objs)

                    lines = []
                    hashtags = []
                    mentions = []
                    
                
                if self.name == "thread0":
                    print(self.name,": monitored",i," users out of",total,"total. Currently using user app number",n_user," followers_app number",n_followers,"retweets_app number",n_retweets,"favorites_app number",n_favorites,"and the last user_id was",user_id,". Iteration number:",iteration,"total number of lines:",total_lines,"dct = ",dct,end = "\r") 
                #break
                # if for 5 times (spaced bt 5 seconds) teh app couldent reconnect follwing a ConnectionError exception, terminate the thread            
                if terminate:
                    break
            #print(" \niteration concluded")
            #iteration += 1
            # pickle mode
#             data = self.loader(self.path)
#             print("BACKUP: len(data) = ", len(data))
#             with open(self.backup_path, "wb") as f:
#                 pickle.dump(data)
                
#             with open
            
            
            # end of pickle mode
            # csv mode (note: it does not support hashtags yet)
#             data = pd.read_csv(self.path)
#             data.to_csv(self.backup_path,index = False)
            # end of csv mode
            

            
            if terminate:
                break
        print(self.name,"FINISHED!!! \n")
        
        
        
        
        
        
        
        
        
        
        
        
# useless
# takes an array of [[user1_id,[user1_follower1_id,user1_follwer2_id,...]],[user2_id,[user2_follower1_id,user2_follwer2_id,...]],...] and writes the edgle list of the nmetwork which nodes are [user1_id,user2_id,...].
class networkThread(Thread):
    def __init__(self, name,nodes, edges,path):
        Thread.__init__(self) 
        self.name = name
        self.nodes  = nodes
        self.edges = edges
        self.path = path
        
    
    def iterable(self, obj):
        try:
            iter(obj)
        except Exception:
            return False
        else:
            return True
        
        
    def run(self):
        print("\n",self.name,"started. Evaluating", len(self.edges),"edges...\n")
        edge_list = [tup for tup in self.edges if tup[1] in self.nodes]
        with open(self.path,"wb") as f:
            np.save(f,np.array(edge_list), allow_pickle=True)
        print(self.name,"finished")
        #return edge_list




        
        
        
        
class AT_Thread(Thread):
    
    retweet_network = []
    unsubscribed_users = set()
    ok_users = set()
    users_objs = []
    active_threads = [] 
    
    
    def __init__(self,name, users, apps,save_path, resource_remaining, resource_reset,wait,saving_thread = "thread0",restart = False):
        Thread.__init__(self)
        self.saving_thread = saving_thread
        self.name = name
        self.users = users
        self.apps = apps
        self.mode  = "user"
        self.save_path = save_path
        self.resource_remaining = resource_remaining
        self.resource_reset = resource_reset
        self.wait  = wait
        
        self.retweet_network_save_path = self.save_path+ "\\" + "retweet_network.txt"
        self.unsubscribed_users_save_path = self.save_path+ "\\" + "unsubscribed_users.txt"
        self.ok_users_save_path = self.save_path+ "\\" + "ok_users.txt"
        self.objs_save_path = self.save_path +"\\"+"objs.txt"

        AT_Thread.active_threads.append(self.name)
        
#         print(self.name, ":reading file", paths[0], "...")
#         with open(paths[0], "rb") as f:
#             self.day0 = pickle.load(f)
#             f.close()
            
        self.restart = restart
        
        if self.restart and self.name=="thread0":
            print(self.name, ": restarting")
            with open(self.unsubscribed_users_save_path, "rb") as f:
                AT_Thread.unsubscribed_users = set(pickle.load(f))
                f.close()
            with open(self.ok_users_save_path, "rb") as f:
                AT_Thread.ok_users = set(pickle.load(f))
                f.close()
            
            
        print(self.name, "constructed")
        
        
        
    def utc_s(self): #https://stackoverflow.com/questions/5998245/get-current-time-in-milliseconds-in-python
        return round(datetime.utcnow().timestamp()) + (60*60*2)

    def logger(self,credentials,mode, wait_on_rate_limit = True):
        #total = len(self.ids)
        retry_count = 1
        retry_delay = 5
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")

    # Fields of user object that we may use to estimate activity: location':"", 'profile_location'=None, 'protected':False,'followers_count': 17,'friends_count': 197,'created_at': 'Sat Sep 28 23:13:30 +0000 2019', 'favourites_count': 28,'statuses_count': 1,follow_request_sent=False

    def get_limits(self,app,path = None):
        limits = app.rate_limit_status()
        if path is not None:
            limit = limits
            for branch in path: 
                limit = limit[branch]
            return limit
        else:
            return limits
        
        
    def test(self,mode = "user",screen_name = "ClaudioMoroni3"):
        i = 0
        apps = self.logger(self.apps, mode = mode ,wait_on_rate_limit = False)
        for app in apps:
            try:
                user = app.get_user(screen_name = screen_name)
                print("app number",i,"authentication succeded")
                i +=1
            except tweepy.TweepError as e:
                print("app number",i,"authentication failed, with reason:", e.response.text)
                i +=1
                
                
                
    def get_date_from_str(self, date_str, as_string = False):
        frmt = "%a %b %d %H:%M:%S %Y" #"%a %b %d %H:%M:%S %z %Y"
        date_str = date_str[:19]+date_str[25:]
        DateTime = datetime.strptime(date_str,frmt)
        if not as_string:
            return DateTime
        else:
            return str(DateTime)
        
                
                
    def compare_dates(self,date_str, datetime):
#         frmt = "%a %b %d %H:%M:%S %Y" #"%a %b %d %H:%M:%S %z %Y"
#         date_str = date_str[:19]+date_str[25:]
#         retrieved_date = datetime.strptime(date_str,frmt)
        retrieved_date  = self.get_date_from_str(date_str, as_string = False)
        #print("retrieved_date = ",retrieved_date,"datetime = ",datetime)
        if retrieved_date == datetime:
            return True
        else:
            return False
        
        
    def save(self):
        if self.name==AT_Thread.active_threads[-1]:
            with open(self.retweet_network_save_path, "ab") as f:
                pickle.dump(AT_Thread.retweet_network, f)
                AT_Thread.retweet_network = []
                #np.save(f,AT_Thread.retweet_network)
                f.close()
            with open(self.unsubscribed_users_save_path, "wb") as f:
                pickle.dump(list(AT_Thread.unsubscribed_users), f)
                f.close()                                      
            with open(self.ok_users_save_path, "wb") as f:
                pickle.dump(list(AT_Thread.ok_users), f)
                f.close()
            with open(self.objs_save_path, "ab") as f:
                pickle.dump(AT_Thread.users_objs,f)
                AT_Thread.users_objs = []
        else:
            pass
        
    
    
        
        
    def run(self):
        print(self.name, "started")
#         retweet_network = []
#         unsubscribed_users = set()
#         ok_users = set()
#         found_users = set()
        n = 0
        
        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
        appFail = False
        all_used = False
        boosts = 0
        day0  = True
        i = 0
        
        
        for user in self.users:
            
#             if day0:
#                 day = self.day0
#                 day0 = False
#             else:
#                 with open(path, "rb") as f:
#                     day = pickle.load(f)
#                     f.close()
                
            total = len(self.users)
            #time.sleep(self.wait)
#             for tweet in day:
            if self.name == self.saving_thread:
                print("Done", i,"out of", total,"users", ". len(retweet_network) =",len(AT_Thread.retweet_network),", len(unsubscribed_users) =",len(AT_Thread.unsubscribed_users),", len(ok_users) =",len(AT_Thread.ok_users),". App number =",n,", boosts =",boosts ,end = "\r")
            user_id = user["user_id"]
                #retrieved_subscription_datetime = tweet["profile_created_at"]
#             if type(tweet["tweet_id"]) == list:
#                 try:
#                     AT_Thread.unsubscribed_users.add(user_id)
#                     i+=1
#                     continue
#                 except:
#                     i+=1
#                 continue
                  
#             if user_id in AT_Thread.unsubscribed_users:
#                 i+=1
#                 boosts += 1
#                 continue

#             if user_id in AT_Thread.ok_users:
#                 index = next((index for (index, d) in enumerate(AT_Thread.retweet_network) if d["user_id"] == user_id), None)
# #                             retweeted_user_id = tweet["retweeted_user_id"]
# #                             retweeted_tweet_id = tweet["retweeted_tweet_id"]
# #                             if type(retweeted_user_id ) != list and type(retweeted_tweet_id) != list:
#                 AT_Thread.retweet_network[index]["retweeted_users_ids"].extend(tweet["retweeted_user_id"]) # to be corrected: extend.. #AT_Thread.retweet_network[index]["retweeted_users_ids"].extend((tweet["retweeted_user_id"],get_date_from_str(tweet["tweet_created_at"]))) 
#                 AT_Thread.retweet_network[index]["retweeted_tweets_ids"].extend(tweet["retweeted_tweet_id"]) # to be corrected: extend..
#                 AT_Thread.retweet_network[index]["hashtags"].append((tweet["hashtags"],self.get_date_from_str(tweet["profile_created_at"], as_string = True))) # to be corrected: extend..
#                 i+=1
#                 boosts += 1
#             else:
                    
            while True:
                try:
                    user_obj = app.get_user(user_id = user_id)
                    if self.compare_dates(user["profile_created_at"], user_obj.created_at): 
                        AT_Thread.retweet_network.append({"user_id":user_id, "user_favorited_count":None, "user_retweeted_count":None, "retweeted_users_ids":user["retweeted_user_id"],"retweeted_tweets_ids":user["retweeted_tweet_id"],"hashtags" :user["hashtags"]}) # , "user_mentions":user["user_mentions"] [(user["hashtags"],self.get_date_from_str(user["profile_created_at"], as_string = True))]})
                        AT_Thread.ok_users.add(user_id)
                        AT_Thread.users_objs.append({"user_id":user_id,'followers_count': user_obj.followers_count,'friends_count': user_obj.friends_count,'created_at': str(user_obj.created_at), 'favourites_count': user_obj.favourites_count,'statuses_count': user_obj.statuses_count})
                        i+=1
                        break
                    else:
                        AT_Thread.unsubscribed_users.add(user_id)
                        i+=1
                        break
            #print("Done") #here...
                except tweepy.RateLimitError:
                    self.save()
                    if not appFail : #mode == "user" and
                        #print("App number",n,"with user auth depleted, authenticationg as app...")
                        self.mode  = "app"
                        app = self.logger(self.apps[n],mode = self.mode ,wait_on_rate_limit = False)
                        remaining = self.get_limits(app,self.resource_remaining)
                        #print("remaining = ", remaining)
                        if remaining == 0 and all_used:
                            wait = self.get_limits(app,self.resource_reset) - self.utc_s()
                            if self.name == self.saving_thread:
                                print(self.name,";sleeping", wait + 10, " seconds to ensure timers are reset...", end = "\n")
                            time.sleep(wait + 10)
                        appFail = True
                        continue
                    else:
                        self.mode  = "user"
                        #print(self.name,"Also app auth of",n,"-th app has been depleted. Switching to next app...")
                        if n == len(self.apps)-1:
                                #if self.name == "thread1":
                                    #print("last app was actually depleted. Restarting from n = 0....",end = "\r")
                            n = 0
                            all_used = True
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0:
                                wait = self.get_limits(app,self.resource_reset)-self.utc_s()
                                if self.name == self.saving_thread:
                                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                time.sleep(wait + 10)
                        else:
                            n = n+1
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0 and all_used:
                                wait = self.get_limits(app,self.resource_reset)-self.utc_s()
                                if self.name == self.saving_thread:
                                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                time.sleep(wait + 10)
                        appFail = False
                        continue
                except ConnectionError as e:
                    if CE_times < 5:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,"\nRelogging the app number",n," for the",CE_times,"time.\n ")
                        time.sleep(5)
                        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                        CE_times += 1
                        continue
                    else:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,". Tried to reconnect for 5 times in a row without success. Skipping user... ")
                        break                
                except tweepy.TweepError as e:
                    if e.api_code == 50: #https://stackoverflow.com/a/48499300 #https://www.programcreek.com/python/?code=SMAPPNYU%2FsmappPy%2FsmappPy-master%2FsmappPy%2Ftweepy_pool.py#   #https://github.com/tweepy/tweepy/issues/1254
                        i = i+1
                        AT_Thread.unsubscribed_users.add(user_id)
                        #print("User",user_id,"not found, skipping...")
                        break
                    else:
                        #print("caught unknown tweepError for user",user_id,": \n",e.response.text,"\nskipping...")
                        AT_Thread.unsubscribed_users.add(user_id)
                        i = i+1
                        break
                except Exception as e:
                    print(self.name,": Exception occurred at user", user_id,"with app number",n)
                    raise e
        self.save()
        AT_Thread.active_threads.remove(self.name)
        print(self.name, "FINISHED \n",)

        
        

# Create a StreamListener 
class MyStreamListener(tweepy.StreamListener):
    
    tweets = []
    users_ids = set()
    tweets_arrived = 0
    
    def __init__(self,name, save_path, users_save_path):
        super().__init__()
        self.keep_alive_arrived = 0
        self.name = name
        self.save_path = save_path
        self.users_save_path = users_save_path
        self.i = 0
        #if restart:
            
        
    def on_status(self, status):
        self.i += 1
        # Set time 
        #t = time.localtime()
        #current_time = time.strftime("%H:%M:%S", t)
        
        hashtags =  [dct["text"] for dct in status.entities["hashtags"]]
        #print("\nStatus arrived at", current_time)
        #print (status.text)
        
        MyStreamListener.users_ids.add(status.user.id)                     # add author id
        #print("AUTHOR ID:", status.user.id)
        #self.hashtags.append(tweet.entities["hashtags"])
        
        
#         if status.in_reply_to_user_id is not None:
#             #print("REPLIED ID:", status.in_reply_to_user_id)
#             self.user_ids.add(status.in_reply_to_user_id)     # add replied id
        
        try:
            retweeted_user_id  = status.retweeted_status.user.id
            #retweeted_user_id = retweeted_status
            MyStreamListener.tweets.append({"user_id":status.user.id, "hashtags":hashtags, "retweeted_user_id":retweeted_user_id})
        except AttributeError:
            MyStreamListener.tweets.append({"user_id":status.user.id, "hashtags":hashtags, "retweeted_user_id":None})
            pass
        
        #np.save("/Users/Pit/GitHub/Econophysics/Project/TwitterMonitor/Streamer_USA/UserIDs/user_ids.npy", np.array(list(self.user_ids))) # PIETRO 1 
        #np.save("/Users/pietromonticone/github/Econophysics/Project/TwitterMonitor/Streamer_USA/UserIDs/user_ids.npy", np.array(list(self.user_ids))) # PIETRO 2
        MyStreamListener.tweets_arrived += 1
        if MyStreamListener.tweets_arrived%500 == 0  : # self.i%25 == 0 and self.name == "thread0"
            with open(self.save_path, "ab") as f:
                pickle.dump(MyStreamListener.tweets,f) # RICCARDO
                MyStreamListener.tweets = []
                f.close()
#             with open(self.users_save_path, "wb") as f:
#                 to_be_saved = list(MyStreamListener.users_ids) #RuntimeError: set changed size during iteration
#                 pickle.dump(to_be_saved,f)
#                 f.close()
            
                
            
        #np.save("C:\Users\Utente\Desktop\Progetti\Python\Econophysics\Project\TwitterMonitor\Streamer_USA\UserIDs\user_ids.npy", np.array(list(self.user_ids))) # DAVIDE
        if self.name== "thread0":
            print("Arrived",MyStreamListener.tweets_arrived, "tweets from", len(MyStreamListener.users_ids),"unique users", end = "\r")
    def keep_alive(self):
        #print("keep alive arrived")
        self.keep_alive_arrived += 1
        
    def on_error(self, status_code):
        print(self.name,"; Error", status_code)
        if status_code == 420:
            #returning False in on_error disconnects the stream
            return False
        return False
    
    

class start_streamer(Thread):
    
    def __init__(self, MyStreamListener, app, ids):
        Thread.__init__(self)
        self.MyStreamListener = MyStreamListener
        self.app = app
        self.ids = ids
        
    def logger(self,credentials,mode, wait_on_rate_limit = True):
        total = len(self.ids)
        retry_count = 1
        retry_delay = 5
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")
        
    def run(self):
        i = 0
        app = self.logger(self.app, mode = "user", wait_on_rate_limit = True )
        #print(self.MyStreamListener.name, "started")
        while True:
            try: 
                print(self.MyStreamListener.name, ": relogging...")
                myStream = tweepy.Stream(auth=app.auth, listener=self.MyStreamListener)

                myStream.filter(
                    follow = [str(ID) for ID in self.ids ],

                    languages=["en"], 

                    is_async=False,

                    stall_warnings=True)
                
            except ProtocolError:
                print(self.MyStreamListener.name,": caught ProtocolError, relogging in ",(2**i)*60 +1, " seconds!")
                time.sleep((2**i)*60 +1)
                i += 1
                continue

            except Exception as e: 
                
                #print(i)
                #Relogging in 10 seconds 
                print(self.MyStreamListener.name, "; Relogging in", (2**i)*60 +1, " seconds!")
                traceback.print_exception(*sys.exc_info()) 
                print(e)
                time.sleep((2**i)*60 +1)
                i += 1
                continue
                #break
                
                
                
# three minutes and a half per 900 tweets (user auth limit, you get other 900 with app auth)
class Hydrator_thread(Thread):
    
    def __init__(self, name, ids, apps, path, save_every, restart = False):
        Thread.__init__(self)
        self.name = name
        self.apps = apps
        #self.ids = ids
        ids = ids.tolist()
        self.ids = [ids[i:i+100] for i in range(0, len(ids), 100)]
        self.save_path = path
        #self.resource = ["resources","statuses","/statuses/show/:id"]
        self.resource = ["resources","statuses","/statuses/lookup"]
        self.resource_remaining = self.resource + ["remaining"]
        self.resource_reset = self.resource + ["reset"]
        self.save_every = save_every
        self.total = len(self.ids)*100
        
        
    
    def utc_s(self): #https://stackoverflow.com/questions/5998245/get-current-time-in-milliseconds-in-python
        return round(datetime.utcnow().timestamp()) + (60*60*2)

    def logger(self,credentials,mode, wait_on_rate_limit = True):
        total = len(self.ids)
        retry_count = 1
        retry_delay = 5
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")

    # Fields of user object that we may use to estimate activity: location':"", 'profile_location'=None, 'protected':False,'followers_count': 17,'friends_count': 197,'created_at': 'Sat Sep 28 23:13:30 +0000 2019', 'favourites_count': 28,'statuses_count': 1,follow_request_sent=False

    def get_limits(self,app,path = None):
        limits = app.rate_limit_status()
        if path is not None:
            limit = limits
            for branch in path: 
                limit = limit[branch]
            return limit
        else:
            return limits
        
    def parse_tweet(self, tweet,path):
        result  = copy.deepcopy(tweet)._json
        #result = result.
        try:
            for field in path:
                result = result[field]
            return result
        except KeyError:
            return []
        
        
        
        
    def run(self):
        hydrated_tweets = []
        i = 0
        n = 0
        app = self.logger(self.apps[n], mode= "user", wait_on_rate_limit = False)
        appFail = False
        print(self.name, "Started with", self.total, "tweet ids to hydrate")
        #for Id in self.ids:
        for Ids in self.ids:
            while True:
                CE_times = 0
                try:
                    
                    tweets = app.statuses_lookup(id_=Ids)
                    
                    #tweet  = app.get_status(Id)
                    #hydrated_tweets.append({"tweet_id":tweet.id,"retweeted_tweet_id":self.parse_tweet(tweet, ["retweeted_status", "id"]),"retweeted_user_id": self.parse_tweet(tweet,["retweeted_status","user","id"]),"text":tweet.text,"user_mentions": [mention["id"] for mention in tweet.entities["user_mentions"]],"user_id":tweet.user.id,"profile_created_at":tweet.user.created_at,'followers_count': tweet.user.followers_count,'friends_count': tweet.user.friends_count, "statuses_count":tweet.user.statuses_count, "favourites_count":tweet.user.favourites_count }) 
                    hydrated_tweets.extend([{"tweet_id":tweet.id,"retweeted_tweet_id":self.parse_tweet(tweet, ["retweeted_status", "id"]),"retweeted_user_id": self.parse_tweet(tweet,["retweeted_status","user","id"]),"hashtags":[dct["text"] for dct in self.parse_tweet(tweet,["entities","hashtags"])],"tweet_created_at":self.parse_tweet(tweet,["created_at"]), "text":tweet.text,"user_mentions": [mention["id"] for mention in tweet.entities["user_mentions"]],"user_id":tweet.user.id,"profile_created_at":tweet.user.created_at,'followers_count': tweet.user.followers_count,'friends_count': tweet.user.friends_count, "statuses_count":tweet.user.statuses_count, "favourites_count":tweet.user.favourites_count } for tweet in tweets]) 
                    i+= 1

                    # save
                    if i%self.save_every == 0:
                        with open(self.save_path, "ab") as f:
                            pickle.dump(hydrated_tweets,f)
                            
                        if self.name == "thread0":
                            print(self.name,": hydrated", i*100, "tweets out of", self.total, end = "\r")

                        hydrated_tweets = []
                    break
                
                except tweepy.RateLimitError:
                    if not appFail : #mode == "user" and
                        #print("App number",n,"with user auth depleted, authenticationg as app...")
                        self.mode  = "app"
                        app = self.logger(self.apps[n],mode = self.mode,wait_on_rate_limit = False)
                        remaining = self.get_limits(app,path = self.resource_remaining)
                        #print("remaining = ", remaining)
                        if remaining == 0 and all_used:
                            wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                            if self.name == "thread1":
                                print(self.name,";sleeping", wait + 10, " seconds to ensure timers are reset...", end = "\n")
                            time.sleep(wait + 10)
                        appFail = True
                        continue
                    else:
                        self.mode  = "user"
                        #print(self.name,"Also app auth of",n,"-th app has been depleted. Switching to next app...")
                        if n == len(self.apps)-1:
                            #if self.name == "thread1":
                                #print("last app was actually depleted. Restarting from n = 0....",end = "\r")
                            n = 0
                            all_used = True
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,path = self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0:
                                wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                if self.name == "thread1":
                                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                time.sleep(wait + 10)
                        else:
                            n = n+1
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,path = self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0 and all_used:
                                wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                if self.name == "thread1":
                                    print("sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                time.sleep(wait + 10)
                        appFail = False
                        continue
                except tweepy.TweepError as e:
                    #if e.api_code == 50: #https://stackoverflow.com/a/48499300 #https://www.programcreek.com/python/?code=SMAPPNYU%2FsmappPy%2FsmappPy-master%2FsmappPy%2Ftweepy_pool.py#   #https://github.com/tweepy/tweepy/issues/1254
                        #i = i+1
                        failed = True
    #                         if self.name == "thread1":
                        #print("User",user_id,"not found, skipping...")
                        #print(self.name, e.api_code)
                        if e.api_code == 326:
                            print(self.name, ": app number",n, "has been deactivated, when i =",i,"and Id = ",Id,"  see error")
                            raise e
                        break
                except ConnectionError as e:
                    if CE_times < 5:
                        print("Caught a  ConnectionError, with reason:\n","\nRelogging the app number",n," for the",CE_times,"time.\n ")
                        time.sleep(5)
                        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                        CE_times += 1
                        continue
                    else:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,". Tried to reconnect for 5 times in a row without success. The tweet id during which the exception occured was",Id,". Exiting...")
                        #terminate = True
                        print(self.name, "caught ConnectionError for the fifth time in a row without being ablr to relog properly, shutting down...")
                        raise e
                        break
                except Exception as e:
                    print(self.name,": Exception occurred at tweet id (approximately)", i*100,"with app number",n)
                    failed = True
                    raise e
        
        print(self.name, ":finished last save_every, remaining_tweets = ", len(hydrated_tweets))
        with open(self.save_path, "ab") as f:
            pickle.dump(hydrated_tweets,f)
        hydrated_tweets = []
                    
        print(self.name, "FINISHED")
            
            
            
            
            

            

            
            
class enterprise_thread(Thread):
    
    def __init__(self, name, min_max_tms ,machines,max_seq, apps,users_ids, path, backup_path,  save_every, restart = False):
        Thread.__init__(self)
        self.name = name
        self.apps = apps
        #self.ids = ids
        #ids = ids.tolist()
        #self.ids = [ids[i:i+100] for i in range(0, len(ids), 100)]
        #metadata = Ec.pickle_loader(metadatum_path)
        self.save_path = path
        self.backup_path = backup_path
        
        if restart:
            print(self.name, ": restart request detected")
            self.min_max_tms = min_max_tms
            print(self.name, ": file loading succeded, thread restarted correctly")
            try:
                last_tms = eval(bin(loader_e(self.save_path )[-1]["tweet_id"] + 1)[:-22]) #eval(bin(tweet_id)[:-22])
                self.min_max_tms[0] = last_tms
            except _pickle.UnpicklingError as e:
                print(self.name, ": main save file corrupted, trying to load from backup... ")
                last_tms = eval(bin(loader_e(self.backup_path)[-1]["tweet_id"] + 1)[:-22]) #eval(bin(tweet_id)[:-22])
                self.min_max_tms[0] = last_tms
                print(self.name, ": backup file loading succeded, thread restarted correctly")
        else:
            self.min_max_tms = min_max_tms
        # array of machine binary codes without "0b"
        self.machines = [f'{machine:010b}' for machine in machines]
        # array of 12bits representing the sequences ("0b" omitted). If you want max 2 tweets per milli, max_seq should be 2
        self.sequences = [f"{i:012b}" for i in range(max_seq)] #https://stackoverflow.com/questions/10411085/converting-integer-to-binary-in-python
        
        # the 10'000 users ids
        self.users_ids = set(users_ids)
        
        
        #self.resource = ["resources","statuses","/statuses/show/:id"]
        self.resource = ["resources","statuses","/statuses/lookup"]
        self.resource_remaining = self.resource + ["remaining"]
        self.resource_reset = self.resource + ["reset"]
        self.save_every = save_every
        # calculate total number of tweet
        self.total = int((min_max_tms[1] - min_max_tms[0])*len(self.machines)*len(self.sequences) - (1/100)*(min_max_tms[1] - min_max_tms[0])*len(self.machines)*len(self.sequences))
        print("Constructed",self.name,"with",len(self.apps),"apps,",self.total,"tweet_ids to hydrate,",len(self.machines),"machines and",len(self.sequences),"sequences" )
        
 
    def utc_s(self): #https://stackoverflow.com/questions/5998245/get-current-time-in-milliseconds-in-python
        # https://www.geeksforgeeks.org/get-utc-timestamp-in-python/#:~:text=Getting%20the%20UTC%20timestamp&text=Use%20the%20datetime.-,datetime.,to%20get%20the%20UTC%20timestamp.
        return round(datetime.utcnow().timestamp()) + (60*60*1) # + (60*60*2)

    def logger(self,credentials,mode, wait_on_rate_limit = True):
        #total = len(self.ids)
        retry_count = 1
        retry_delay = 5
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")

    # Fields of user object that we may use to estimate activity: location':"", 'profile_location'=None, 'protected':False,'followers_count': 17,'friends_count': 197,'created_at': 'Sat Sep 28 23:13:30 +0000 2019', 'favourites_count': 28,'statuses_count': 1,follow_request_sent=False

    def get_limits(self,app,path = None):
        limits = app.rate_limit_status()
        if path is not None:
            limit = limits
            for branch in path: 
                limit = limit[branch]
            return limit
        else:
            return limits
        
    def parse_tweet(self, tweet,path):
        result  = copy.deepcopy(tweet)._json
        #result = result.
        try:
            for field in path:
                result = result[field]
            return result
        except KeyError:
            return []
    
    # this function generates the next timestamp, without re-generating the AT ones
    def next_timestamp(self): # https://stackoverflow.com/questions/231767/what-does-the-yield-keyword-do
        current_tms = self.min_max_tms[0]
        while current_tms < self.min_max_tms[1]:
            current_tms += 1
            while str(current_tms)[-3:-1] == "00":
                current_tms += 1
            yield bin(current_tms)
            
        
    def next_id(self):
        for tms in self.next_timestamp():
            for mach in self.machines:
                for seq in self.sequences:
                    yield eval(tms+mach+seq)
                    
    def next_batch(self):
        batch = []
        for Id in self.next_id():
            batch.append(Id)
            if len(batch) == 100:
                yield batch
                batch = []
        
        
        
        
    def run(self):
        hydrated_tweets = []
        i = 0
        n = 0
        app = self.logger(self.apps[n], mode= "user", wait_on_rate_limit = False)
        appFail = False
        all_used = False
        total_found = 0
        print(self.name, "Started with", self.total, "tweet ids to hydrate")
        #for Id in self.ids:
        for Ids in self.next_batch():
            while True:
                CE_times = 0
                try:
                    
                    tweets = app.statuses_lookup(id_=Ids)
                    
                    #tweet  = app.get_status(Id)
                    #hydrated_tweets.append({"tweet_id":tweet.id,"retweeted_tweet_id":self.parse_tweet(tweet, ["retweeted_status", "id"]),"retweeted_user_id": self.parse_tweet(tweet,["retweeted_status","user","id"]),"text":tweet.text,"user_mentions": [mention["id"] for mention in tweet.entities["user_mentions"]],"user_id":tweet.user.id,"profile_created_at":tweet.user.created_at,'followers_count': tweet.user.followers_count,'friends_count': tweet.user.friends_count, "statuses_count":tweet.user.statuses_count, "favourites_count":tweet.user.favourites_count }) 
                    hydrated_tweets.extend([{"tweet_id":tweet.id,"retweeted_tweet_id":self.parse_tweet(tweet, ["retweeted_status", "id"]),"retweeted_user_id": self.parse_tweet(tweet,["retweeted_status","user","id"]),"hashtags":[dct["text"] for dct in self.parse_tweet(tweet,["entities","hashtags"])],"tweet_created_at":self.parse_tweet(tweet,["created_at"]), "text":tweet.text,"user_mentions": [mention["id"] for mention in tweet.entities["user_mentions"]],"user_id":tweet.user.id,"profile_created_at":tweet.user.created_at,'followers_count': tweet.user.followers_count,'friends_count': tweet.user.friends_count, "statuses_count":tweet.user.statuses_count, "favourites_count":tweet.user.favourites_count } for tweet in tweets if tweet.user.id in self.users_ids]) #if tweet.user.id in self.users_ids
                    i+= 1
                    total_found += len(hydrated_tweets)
                    # save
                    if i%self.save_every == 0:
                        with open(self.save_path, "ab") as f:
                            pickle.dump(hydrated_tweets,f)
                            f.close()
                        with open(self.backup_path, "ab") as f:
                            pickle.dump(hydrated_tweets,f)
                            f.close()
                            
                        if self.name == "thread0":
                            print(self.name,": hydrated", i*100, "tweets out of", self.total,". Found",total_found,"tweets in total.", end = "\r")

                        hydrated_tweets = []
                    break
                
                except tweepy.RateLimitError:
                    if not appFail : #mode == "user" and
                        #print("App number",n,"with user auth depleted, authenticationg as app...")
                        self.mode  = "app"
                        app = self.logger(self.apps[n],mode = self.mode,wait_on_rate_limit = False)
                        remaining = self.get_limits(app,path = self.resource_remaining)
                        #print("remaining = ", remaining)
                        if remaining == 0 and all_used:
                            wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                            if self.name == "thread0":
                                print("\n",self.name,": sleeping", wait + 10, " seconds to ensure timers are reset...", end = "\n")
                            if wait >= 0:
                                time.sleep(wait + 10)
                                #print(self.name,": Resuming...")
                        appFail = True
                        continue
                    else:
                        self.mode  = "user"
                        if self.name == "thread0":
                            print("\n", self.name,"Also app auth of",n,"-th app has been depleted. Switching to next app...")
                        if n == len(self.apps)-1:
                            #if self.name == "thread1":
                                #print("last app was actually depleted. Restarting from n = 0....",end = "\r")
                            n = 0
                            all_used = True
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,path = self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0:
                                wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                if self.name == "thread0":
                                    print("\n", self.name,": sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                if wait >= 0:
                                    time.sleep(wait + 10)
                                    #print(self.name,": Resuming...")
                        else:
                            n = n+1
                            app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                            remaining = self.get_limits(app,path = self.resource_remaining)
                            #print("remaining = ", remaining)
                            if remaining == 0 and all_used:
                                wait = self.get_limits(app,path = self.resource_reset) - self.utc_s()
                                #if self.name == "thread1":
                                print(self.name,": sleeping",wait + 10," seconds to ensure timers are reset...",end = "\n")
                                if wait >= 0:
                                    time.sleep(wait + 10)
                                    #print(self.name,": Resuming...")
                        appFail = False
                        continue
                except tweepy.TweepError as e:
                    #if e.api_code == 50: #https://stackoverflow.com/a/48499300 #https://www.programcreek.com/python/?code=SMAPPNYU%2FsmappPy%2FsmappPy-master%2FsmappPy%2Ftweepy_pool.py#   #https://github.com/tweepy/tweepy/issues/1254
                        #i = i+1
                        failed = True
    #                         if self.name == "thread1":
                        #print("User",user_id,"not found, skipping...")
                        #print(self.name, e.api_code)
                        if e.api_code == 326:
                            print(self.name, ": app number",n, "has been deactivated, when i =",i,"and Id = ",Id,"  see error")
                            raise e
                        break
                except ConnectionError as e:
                    if CE_times < 5:
                        print("Caught a  ConnectionError, with reason:\n","\nRelogging the app number",n," for the",CE_times,"time.\n ")
                        time.sleep(5)
                        app = self.logger(self.apps[n],mode = self.mode, wait_on_rate_limit = False)
                        CE_times += 1
                        continue
                    else:
                        print("Caught a  ConnectionError, with reason:\n", e.reason,". Tried to reconnect for 5 times in a row without success. The tweet id during which the exception occured was",Id,". Exiting...")
                        #terminate = True
                        print(self.name, "caught ConnectionError for the fifth time in a row without being ablr to relog properly, shutting down...")
                        raise e
                        break
                except Exception as e:
                    print(self.name,": Exception occurred at tweet id (approximately)", i*100,"with app number",n)
                    failed = True
                    raise e
        
        print(self.name, ":finished last save_every, remaining_tweets = ", len(hydrated_tweets))
        with open(self.save_path, "ab") as f:
            pickle.dump(hydrated_tweets,f)
            f.close()
        with open(self.backup_path, "ab") as f:
            pickle.dump(hydrated_tweets,f)
            f.close()
        hydrated_tweets = []
                    
        print(self.name, "FINISHED")
            




##############################
##### UTILITY FUNCTIONS #####
##############################


#### THREAD MANAGEMENT ####

def get_threads(n_threads,thread,path_start,path_end,ids,apps,resource, restart = False, **kwargs):  #https://realpython.com/python-kwargs-and-args/
    ids_splits = split_array(ary = ids, indices_or_sections = n_threads)
    apps_splits = split_array(ary = apps, indices_or_sections = n_threads)
    apps_splits  = [split.tolist() for split in apps_splits]
    names  = ["thread"+str(i) for i in range(n_threads)]
    paths = [path_start + str(i) +path_end for i in range(n_threads)]
    #return apps_splits
    return [thread(name = naip[0], apps = naip[1], ids = naip[2], path = naip[3], resource_remaining = resource + ["remaining"], resource_reset = resource + ["reset"], restart= False, **kwargs) for naip in list(zip(names,apps_splits,ids_splits,paths))]


def get_monitor_threads(n_threads ,apps, path_start,save_every ,objs = None, restart = False, frmt_temporal = ".txt", frmt_objs = ".npy"):  #name,apps,objs,path,backup_path,objs_save_path ,objs_backup_path, hashtags_path,hashtags_backup_path, restart = False
    
    
    apps_splits = split_array(ary = apps, indices_or_sections = n_threads)
    apps_splits  = [split.tolist() for split in apps_splits]
    names  = ["thread"+str(i) for i in range(n_threads)]
    
    save_path_start = path_start + r"\monitor\csvs\threading_csvs\temporal_"
    save_paths = [save_path_start + str(i) +frmt_temporal for i in range(n_threads)]
    backup_path_start = path_start +r"\monitor\csvs\threading_csvs\backup\temporal_"#r"\monitor\csvs\backup\threading_csvs\temporal_"
    backup_paths  = [backup_path_start + str(i) +frmt_temporal for i in range(n_threads)]

    hashtags_save_path = path_start +r"\monitor\hashtags\threading_hashtags\hashtags_" #r"\monitor\csvs\threading_csvs\hashtags_"
    hashtags_paths = [hashtags_save_path+ str(i) +frmt_temporal for i in range(n_threads)]
    hashtags_backup_path = path_start +r"\monitor\hashtags\threading_hashtags\backup\hashtags_" #r"\monitor\csvs\backup\threading_csvs\hashtags_"
    hashtags_backup_paths  = [hashtags_backup_path + str(i) +frmt_temporal for i in range(n_threads)]

    mentions_save_path = path_start +r"\monitor\mentions\threading_mentions\mentions_" #r"\monitor\csvs\threading_csvs\hashtags_"
    mentions_paths = [mentions_save_path+ str(i) +frmt_temporal for i in range(n_threads)]
    mentions_backup_path = path_start +r"\monitor\mentions\threading_mentions\backup\mentions_" #r"\monitor\csvs\backup\threading_csvs\hashtags_"
    mentions_backup_paths  = [mentions_backup_path + str(i) +frmt_temporal for i in range(n_threads)]

    objs_save_path_start = path_start +r"\monitor\monitor_objs\threading_objs\monitor_objs_"
    objs_save_paths = [objs_save_path_start + str(i) +frmt_objs for i in range(n_threads)]
    objs_backup_path_start  = path_start +r"\monitor\monitor_objs\threading_objs\backup\monitor_objs_"
    objs_backup_paths = [objs_backup_path_start  + str(i) +frmt_objs for i in range(n_threads)]
    
    if objs is not None:
        objs_splits = split_array(ary = objs, indices_or_sections = n_threads)

        return [TwitterThreadMonitor(name = naosboohhmm[0], apps = naosboohhmm[1], objs = naosboohhmm[2], path = naosboohhmm[3],backup_path = naosboohhmm[4],objs_save_path = naosboohhmm[5] ,objs_backup_path = naosboohhmm[6],hashtags_path =naosboohhmm[7] ,hashtags_backup_path =naosboohhmm[8] ,mentions_path =naosboohhmm[9],mentions_backup_path =naosboohhmm[10] , save_every = save_every, restart= restart) for naosboohhmm in list(zip(names,apps_splits,objs_splits,save_paths,backup_paths,objs_save_paths,objs_backup_paths,hashtags_paths,hashtags_backup_paths, mentions_paths, mentions_backup_paths))]
    
    else:
        
        return [TwitterThreadMonitor(name = nasboohhmm[0], apps = nasboohhmm[1], objs = None, path = nasboohhmm[2],backup_path = nasboohhmm[3],objs_save_path = nasboohhmm[4] ,objs_backup_path = nasboohhmm[5],hashtags_path =nasboohhmm[6] ,hashtags_backup_path =nasboohhmm[7] ,mentions_path =nasboohhmm[8],mentions_backup_path =nasboohhmm[9] , save_every = save_every, restart= restart) for nasboohhmm in list(zip(names,apps_splits,save_paths,backup_paths,objs_save_paths,objs_backup_paths,hashtags_paths,hashtags_backup_paths, mentions_paths, mentions_backup_paths))]
        
    
    

    
def get_AT_threads(n_threads,users,apps,resource, save_path, restart = False):
    #paths_splits = split_array(ary = paths, indices_or_sections = n_threads)
    users_splits = split_array(ary =users, indices_or_sections = n_threads)
    apps_splits = split_array(ary = apps, indices_or_sections = n_threads)
    apps_splits  = [split.tolist() for split in apps_splits]
    names  = ["thread"+str(i) for i in range(n_threads)]
    waits = [i*10 + 1 for i in range(n_threads) ]
    waits.reverse()
    return [AT_Thread(name = naip[0], apps = naip[1], users = naip[2],wait = naip[3],save_path = save_path, resource_remaining = resource + ["remaining"], resource_reset = resource + ["reset"], restart= False) for naip in list(zip(names,apps_splits,users_splits,waits))]



def get_follow_streamer_threads(ids, apps, save_path, users_save_path):
    splits = len(ids)//5000 + 1
    print("starting",splits ,"threads")
    ids_splits = split_array(ary = ids, indices_or_sections = splits)
    apps_splits = [app for app in apps[:splits]]
    names = ["thread"+str(i) for i in range(splits)]
    stream_listeners  = [MyStreamListener(name = n, save_path = save_path, users_save_path = users_save_path) for n in names]
    return [start_streamer(MyStreamListener = mai[0], app = mai[1], ids = mai[2] ) for mai in zip(stream_listeners, apps_splits,ids_splits)]



def get_hydrator_threads(n_threads,path_start,ids,apps,save_every = 100, restart = False, **kwargs):  #https://realpython.com/python-kwargs-and-args/
    ids_splits = split_array(ary = ids, indices_or_sections = n_threads)
    apps_splits = split_array(ary = apps, indices_or_sections = n_threads)
    apps_splits  = [split.tolist() for split in apps_splits]
    names  = ["thread"+str(i) for i in range(n_threads)]
    paths = [path_start + str(i) +".txt" for i in range(n_threads)]
    #return apps_splits
    return [Hydrator_thread(name = naip[0], apps = naip[1], ids = naip[2], path = naip[3], save_every = save_every, restart= False, **kwargs) for naip in list(zip(names,apps_splits,ids_splits,paths))]




# evaluate max sequence ( defined as the average + std rounded to unity)
def get_max_seq(metadatum):
    return np.sum([key*value for key,value in metadatum["sequences_counter"].items()])/np.sum([value for value in metadatum["sequences_counter"].values()])  + np.std(np.repeat(list(metadatum["sequences_counter"].keys()),list(metadatum["sequences_counter"].values()) ))


# creat enterprise threads
def get_enterprise_threads(n_threads, apps, metadata_path, users_ids_path, path_start, name, restart = False):
    threads = []
    paths = get_listOfFiles(metadata_path)
    if n_threads < len(paths):
        print("minimum number of threads must coincide with number of metadata. Setting n_threads to",len(paths),"...")
        n_threads = len(paths)
    # collect metadata and repeeat them n_theads/len(paths) times each
    metadata = [pickle_loader(path) for path in paths]#np.repeat([Ec.pickle_loader(path) for path in paths], int(n_threads/len(paths) ))

    proportions = [(metadatum["timestamps_delta_regularity"][0]- metadatum["timestamps_delta_regularity"][1]) * len(metadatum["unique_machines"].keys()) * int(get_max_seq(metadatum)) for metadatum in metadata]
    total = sum(proportions)
    proportions = [0] + list(np.cumsum([proportion/total for proportion in proportions]))#[proportion/total for proportion in proportions] #
    #print(total)
    #print(np.array(proportions)*len(apps))
    threads_apps = split_array(apps, n_threads)
    threads_save_paths = [path_start + r"\\" + name+ str(i) +".txt" for i in range(n_threads)]
    thread_backup_paths = [path_start + r"\backup\\" +name+  str(i) +".txt" for i in range(n_threads)]
    threads_names = ["thread"+str(i) for i in range(n_threads)]
    apps_splits = []
    names_splits = []
    save_paths_splits = []
    backup_paths_splits = []
    for i in range(len(proportions)-1):
        #print(ceil(proportions[i]*len(threads_apps)))
        apps_splits.append( threads_apps[ int(proportions[i]*len(threads_apps)) : int(proportions[i+1]*len(threads_apps)) ] )
        names_splits.append(threads_names[ int(proportions[i]*len(threads_names)) : int(proportions[i+1]*len(threads_names)) ])
        save_paths_splits.append(threads_save_paths[ int(proportions[i]*len(threads_save_paths)) : int(proportions[i+1]*len(threads_save_paths)) ])
        backup_paths_splits.append(thread_backup_paths[ int(proportions[i]*len(thread_backup_paths)) : int(proportions[i+1]*len(thread_backup_paths)) ])
    #print(len(apps_splits),len(metadata),len(names_splits),len(save_paths_splits))

    users_ids = np.load(users_ids_path, allow_pickle = True)
    

    #visualize splits
    print("names_splits = ",names_splits)
    
    #distribute threads  
    for names_split, apps_split, metadatum, paths_split, backup_split in zip(names_splits, apps_splits, metadata,save_paths_splits,backup_paths_splits):
        #print("len(names_split) = ",len(names_split))
        print("-----------------------------------------")
        
        # evaluate max seq
        max_seq = int(get_max_seq(metadatum))
        
        # distribute tweet ids 
        increase = (metadatum["timestamps_delta_regularity"][0] - metadatum["timestamps_delta_regularity"][1])/len(names_split)
        min_max_tms_split = [[int(metadatum["timestamps_delta_regularity"][1] + i*increase) , int(metadatum["timestamps_delta_regularity"][1] + (i+1)*increase)] for i in range(len(names_split))] 
        #print("len(min_max_tms_split) = ",len(min_max_tms_split))
        # create threads
        threads.extend([enterprise_thread(name = nmapb[0], min_max_tms = nmapb[1], machines = list(metadatum["unique_machines"].keys()),max_seq =  max_seq, apps = nmapb[2] ,users_ids  = users_ids ,path = nmapb[3], backup_path = nmapb[4], save_every = 10, restart = restart) for nmapb in zip(names_split,min_max_tms_split, apps_split,paths_split, backup_split)])
    return threads



def start_threads(threads, wait = 0):
    for thread in threads:
        thread.start()
        time.sleep(wait)
        
    for thread in threads:
        thread.join()


def logger(credentials,mode, wait_on_rate_limit = True):
        retry_count = 0
        retry_delay = 1 #15*60 + 10
        apps = []
        if type(credentials[0]) == list:
            #print("logging multiple apps as",mode)
            for cred in credentials: # cred is the list of the 2 dicts for each app
                if mode == "user":
                    try:
                        auth = tweepy.OAuthHandler(**cred[0])
                        auth.set_access_token(**cred[1])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401,429, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                elif mode == "app":
                    try:
                        auth = tweepy.AppAuthHandler(**cred[0])
                        app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401,429, 500, 503,10054]) ) #404
                        apps.append(app)
                    except:
                        #print("logging error accured at app with credentials:", cred)
                        return
                else:
                    #print("mode must be one of 'user' or 'app'")
                    return
            #print("done")
            return apps
        elif type(credentials[0]) == dict:
            #print("logging only one app as", mode)
            if mode == "user":
                try:
                    auth = tweepy.OAuthHandler(**credentials[0])
                    auth.set_access_token(**credentials[1])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit ,wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401,429, 500, 503,10054]) ) #404 #retry_count = 5, retry_delay = 10
                    #apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            elif mode == "app":
                try:
                    auth = tweepy.AppAuthHandler(**credentials[0])
                    app = tweepy.API(auth, wait_on_rate_limit = wait_on_rate_limit , wait_on_rate_limit_notify = True, retry_count = retry_count, retry_delay = retry_delay, retry_errors=set([401,429, 500, 503,10054]) ) #404
                    apps.append(app)
                except:
                    #print("logging error accured at app with credentials:", credentials)
                    return
            else:
                #print("mode must be one of 'user' or 'app'")
                return
            #print("done")
            return app
        else:
            print("invalid credentials argument: it must be a list of lists of two dicts for multiple logging or a list of two dicts for single app logging")





def followers_loader(path): #inspired by rw_to_TwitterThread
    with open(path, "rb") as f:
        rw_ids_raw = []
        while 1:
            try:
                rw_ids_raw.append(pickle.load(f))
            except EOFError:
                break
        f.close()
    return np.array(rw_ids_raw)


        
        
        
def rw_to_TwitterThread(path):
    with open(path, "rb") as f:
        rw_ids_raw = []
        while 1:
            try:
                rw_ids_raw.append(pickle.load(f))
            except EOFError:
                break
        f.close()
        
        
    rw_ids = []
    for couple in rw_ids_raw:
        rw_ids.append(couple[0])
        rw_ids.extend(couple[1])
        
    return np.unique(np.array(rw_ids))




#load a file of dicts as saved by TwitterThreadOBJ and return it as an array of dicts  them like this: https://stackoverflow.com/questions/12761991/how-to-use-append-with-pickle-in-python
def loader_a(path):
    with open(path, "rb") as f:
        objs = []
        while 1:
            try:
                objs.append(pickle.load(f))
            except EOFError:
                break
        f.close()

    #objs = [x for y in objs for x in y]
    #print(len(objs))


    return np.array(objs)
    # print(len(np.unique(objs_np)))
    
    

def loader_e(path):
    with open(path, "rb") as f:
        objs = []
        while 1:
            try:
                objs.extend(pickle.load(f))
            except EOFError:
                break
        f.close()

    #objs = [x for y in objs for x in y]
    #print(len(objs))


    return np.array(objs)
    # print(len(np.unique(objs_np)))
    
def pickle_loader(path):
    with open(path, "rb") as f:
        final = pickle.load(f)
        f.close()
    return final


def pickle_dumper(path, obj, mode = "ab"):
    with open(path, mode) as f:
        pickle.dump(obj,f)
        f.close()
    
    
def objs_loader(path):
    with open(path, "rb") as f:
        objs = []
        while 1:
            try:
                objs.append(pickle.load(f))
            except EOFError:
                break
        f.close()

    objs = [x for y in objs for x in y]
    #print(len(objs))


    return np.array(objs)
    
    
def txt_unifier(threading_folder, destination_folder, name):
    paths = [threading_folder +"\\"+ file for file in os.listdir(threading_folder) if file != "notes.txt" and file != "backup"]
    result = np.concatenate([loader(path) for path in paths])
    np.save(destination_folder + "\\" + name + ".npy", result)
    
    
    
def objs_txt_unifier(threading_folder, destination_folder, name, mode):
    print("reading...")
    paths = [threading_folder +"\\"+ file for file in os.listdir(threading_folder) if file != "notes.txt" and file != "backup"]
    print("concatenating")
    if mode == "a":
        result = np.concatenate([loader_a(path) for path in paths])  #objs_loader
    elif mode == "e":
        result = np.concatenate([loader_e(path) for path in paths])  #objs_loader
    print("saving")
    np.save(destination_folder + "\\" + name + ".npy", result)
    
    
def objs_txt_unifier_only_ids(threading_folder, destination_folder, name, mode, ret = False):
    print("reading...")
    paths = [threading_folder +"\\"+ file for file in os.listdir(threading_folder) if file != "notes.txt" and file != "backup"]
    print("concatenating")
    if mode == "a":
        result = np.concatenate([[user["user_id"] for user in loader_a(path)] for path in paths])  #objs_loader
    elif mode == "e":
        result = np.concatenate([[user["user_id"] for user in loader_e(path)] for path in paths])  #objs_loader
    print("saving")
    np.save(destination_folder + "\\" + name + ".npy", result)
    if ret:
        return result
    else:
        return
    

# returns list of absolute file paths contained in folder,and in all subfolders of folder
def get_listOfFiles(folder):
    listOfFiles= list()
    for (dirpath, dirnames, filenames) in os.walk(folder):
        listOfFiles += [os.path.join(dirpath, file) for file in filenames]
    return listOfFiles

#

def get_monitor_objects(retweet_sample_path, followers_sample_path, favorite_sample_path, save_path = None, return_objs = True ,truncated = True ):
    
    data = ( np.load(followers_sample_path, allow_pickle = True), np.load(retweet_sample_path, allow_pickle = True), np.load(favorite_sample_path,allow_pickle = True) )

    sets = [set([user["user_id"] for user in network]) for network in data]
    sample_ids_set = set(sets[0]).intersection(*sets) #set([user["user_id"] for user in shortest])
    followers_sample_sorted = sorted([user for user in data[0] if user["user_id"] in sample_ids_set], key = lambda user: user["user_id"])
    retweets_sample_sorted = sorted([user  for user in data[1] if user["user_id"] in sample_ids_set],key = lambda user: user["user_id"])
    favorite_sample_sorted = sorted([user  for user in data[2] if user["user_id"] in sample_ids_set],key = lambda user: user["user_id"])
    # check the sorting (0 = ok)
    a = sum([1 if couple[0]["user_id"] != couple[1]["user_id"] or couple[0]["user_id"] != couple[2]["user_id"]  else 0 for couple in list(zip(followers_sample_sorted,retweets_sample_sorted, favorite_sample_sorted))])
    if  a== 0:
        print("checksum succeded")
    else:
        print("checksum failed, some elements are missing",a)

    # build and save the final dict
    if truncated:
        monitor_dict = np.array([{"user_id":user[0]["user_id"] ,"followers_ids":user[0]["followers_ids"][:5000], "retweeted_users_ids":user[1]["retweeted_users_ids"][:40],"retweeted_tweets_ids":user[1]["retweeted_tweets_ids"][:40], "hashtags":user[1]["hashtags"][:40], "favorited_users_ids":user[2]["favorited_users_ids"][:60],"favorited_tweets_ids":user[2]["favorited_tweets_ids"][:60]} for user in zip(followers_sample_sorted,retweets_sample_sorted,favorite_sample_sorted)]) 
    else: 
        monitor_dict = np.array([{"user_id":user[0]["user_id"] ,"followers_ids":user[0]["followers_ids"], "retweeted_users_ids":user[1]["retweeted_users_ids"],"retweeted_tweets_ids":user[1]["retweeted_tweets_ids"],"hashtags":user[1]["hashtags"], "favorited_users_ids":user[2]["favorited_users_ids"],"favorited_tweets_ids":user[2]["favorited_tweets_ids"]} for user in zip(followers_sample_sorted,retweets_sample_sorted,favorite_sample_sorted)]) # "favorited_users" to be added
    if save_path is not None:
        np.save(save_path, monitor_dict)
    if return_objs:
        return monitor_dict
    
    
    
    

def get_fast_monitor_objects(objs_sample_path, retweet_sample_path, followers_sample_path, favorite_sample_path, save_path = None, return_objs = True ,truncated = True ):
    
    data = (np.load(followers_sample_path, allow_pickle = True), np.load(retweet_sample_path, allow_pickle = True), np.load(favorite_sample_path,allow_pickle = True),np.load(objs_sample_path, allow_pickle = True) )

    sets = [set([user["user_id"] for user in network]) for network in data]
    sample_ids_set = set(sets[0]).intersection(*sets) #set([user["user_id"] for user in shortest])
    followers_sample_sorted = sorted([user for user in data[0] if user["user_id"] in sample_ids_set],key = lambda user: user["user_id"])
    retweets_sample_sorted  = sorted([user for user in data[1] if user["user_id"] in sample_ids_set],key = lambda user: user["user_id"])
    favorite_sample_sorted  = sorted([user for user in data[2] if user["user_id"] in sample_ids_set],key = lambda user: user["user_id"])
    objs_sample_sorted      = sorted([user for user in data[3] if user["user_id"] in sample_ids_set],key = lambda user: user["user_id"])
    # check the sorting (0 = ok)
    a = sum([1 if couple[0]["user_id"] != couple[1]["user_id"] or couple[0]["user_id"] != couple[2]["user_id"] or couple[0]["user_id"] != couple[3]["user_id"]  else 0 for couple in list(zip(followers_sample_sorted,retweets_sample_sorted, favorite_sample_sorted, objs_sample_sorted))])
    if  a== 0:
        print("checksum succeded")
    else:
        print("checksum failed, some elements are missing",a)

    # build and save the final dict
    if truncated:
        monitor_dict = np.array([{"user_id":user[0]["user_id"] ,"followers_count":user[3]["followers_count"][:5000], "statuses_count":user[3]["statuses_count"][:40],"favourites_count":user[3]["favourites_count"][:60],"followers_ids":user[0]["followers_ids"][:5000], "retweeted_users_ids":user[1]["retweeted_users_ids"][:40],"retweeted_tweets_ids":user[1]["retweeted_tweets_ids"][:40], "favorited_users_ids":user[2]["favorited_users_ids"][:60],"favorited_tweets_ids":user[2]["favorited_tweets_ids"][:60], "tweets_ids":user[1]["tweets_ids"]} for user in zip(followers_sample_sorted,retweets_sample_sorted,favorite_sample_sorted,objs_sample_sorted)]) #"hashtags":user[1]["hashtags"][:40],
    else: 
        monitor_dict = np.array([{"user_id":user[0]["user_id"] ,"followers_count":user[3]["followers_count"], "statuses_count":user[3]["statuses_count"],"favourites_count":user[3]["favourites_count"],"followers_ids":user[0]["followers_ids"][:15000], "retweeted_users_ids":user[1]["retweeted_users_ids"],"retweeted_tweets_ids":user[1]["retweeted_tweets_ids"],"favorited_users_ids":user[2]["favorited_users_ids"],"favorited_tweets_ids":user[2]["favorited_tweets_ids"], "tweets_ids":user[1]["tweets_ids"]} for user in zip(followers_sample_sorted,retweets_sample_sorted,favorite_sample_sorted,objs_sample_sorted)]) # "favorited_users" to be added #"hashtags":user[1]["hashtags"]
    if save_path is not None:
        np.save(save_path, monitor_dict)
    if return_objs:
        return monitor_dict
    
    
    

   

def get_limits(app,path = None):
    limits = app.rate_limit_status()
    if path is not None:
        limit = limits
        for branch in path: 
            limit = limit[branch]
        return limit
    else:
        return limits
    
    
def test(apps, mode = "user",screen_name = "ClaudioMoroni5"):
    i = 0
    apps = logger(apps, mode = mode ,wait_on_rate_limit = False)
    for app in apps:
        try:
            user = app.get_user(screen_name = screen_name)
            print("app number",i,"authentication succeded")
            i +=1
        except tweepy.TweepError as e:
            print("app number",i,"authentication failed, with reason:", e.response.text)
            i +=1


    
    
#### NETWORK ANALYSIS ####



def omit_by(dct, predicate=lambda x: x!=0):
    return {k: v for k, v in dct.items() if predicate(v)}

def log_bin(dict,n_bins):
    
    # first we need to define the interval of dict values
    min_val=sorted(dict.values())[0]
    max_val=sorted(dict.values())[-1]
    delta=(math.log(float(max_val))-math.log(float(min_val)))/n_bins
    
    # then we create the bins, in this case the log of the bins is equally spaced (bins size increases exponentially)
    bins=np.zeros(n_bins+1,float)
    bins[0]=min_val
    for i in range(1,n_bins+1):
        bins[i]=bins[i-1]*math.exp(delta)
        
    
    # then we need to assign the dict of each node to a bin
    values_in_bin=np.zeros(n_bins+1,float)
    nodes_in_bin=np.zeros(n_bins+1,float)  # this vector is crucial to evalute how many nodes are inside each bin
        
    for i in dict:
        for j in range(1,n_bins+1):
            if j<n_bins:
                if dict[i]<bins[j]:
                    values_in_bin[j]+=dict[i]
                    nodes_in_bin[j]+=1.
                    break
            else:
                if dict[i]<=bins[j]:
                    values_in_bin[j]+=dict[i]
                    nodes_in_bin[j]+=1.
                    break
    
    
    # then we need to evalutate the average x value in each bin
    
    for i in range(1,n_bins+1):
        if nodes_in_bin[i]>0:
            values_in_bin[i]=values_in_bin[i]/nodes_in_bin[i]
            
    # finally we get the binned distribution        
            
    binned=[]
    for i in range(1,n_bins+1):
        if nodes_in_bin[i]>0:
                x=values_in_bin[i]
                y=nodes_in_bin[i]/((bins[i]-bins[i-1])*len(dict))
                binned.append([x,y])
    return binned


def get_view(users_objs, which, w = [1,1,1]):
    if which == "degree":
        view = {int(obj["user_id"]):int(obj["followers_count"])+int(obj["friends_count"]) for obj in users_objs }
    elif which == "in_degree":
        try:
            view = {int(obj["user_id"]):int(obj["friends_count"]) for obj in users_objs } 
        except:
            print("Error, check the degree sequence! Is it directed?")
    elif which == "out_degree":
        try: 
            view = {int(obj["user_id"]):int(obj["followers_count"]) for obj in users_objs } 
        except:
            print("error, check the degree sequence! Is it directed?")
    elif which == "activity_from_metadata":
        now = datetime.utcnow().timestamp()
        view = {obj["user_id"]:(w[0]*float(obj["statuses_count"])+w[1]*float(obj["favourites_count"])+w[2]*float(obj["friends_count"]))/((now-datetime.strptime(obj["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())/(60*60*24)) for obj in users_objs}
    else:
        print("Invalid 'which' argument: it must be one of 'degree', 'in_degree', 'out_degree' or 'activity_from_metadata'")
        return
    
    mean = np.mean(np.array(list(view.values())))
    var  = np.var(np.array(list(view.values())))
    
    return (view, mean, var)



def plot_distribution_from_view(view, which = None, rounding  = 2, hist = True, bins = None, kde = True, log_binning = None, color = 'darkblue', hist_kws={'edgecolor':'black'}, kde_kws={'linewidth': 3}, title = "", log = False, dimensions = (15,8), display_stats = None):
    """
    """
    plt.rcParams['figure.figsize'] = dimensions
    if log_binning is not None:
        if bins is not None:
            raise Exception("bins parameter is automatically determined if log_binning is set to True, so the specified value will be ignored.\n")
        view_nonzero = omit_by(dct = view)
        log_distrib = log_bin(view_nonzero,log_binning)
        bins = [0]+[lim[0] for lim in log_distrib]

#     else:
#         bins = None
    if which is not None:
        counts = [round(obj[which],rounding) for obj in view]
    else:
        counts = [round(value) for value in list(view.values())]
        x = list(view.keys())
    #try:
    ax = sns.distplot(counts, hist = hist, kde = kde, bins = bins , color = color, hist_kws = hist_kws , kde_kws =  kde_kws,x = x)
    #except:
        
    ax.set_title(title, fontsize = 16)
    ax.set_xlabel("$k$", fontsize = 14)
    ax.set_ylabel("$P(k)$", fontsize = 14)
    ax.tick_params(labelsize  = 11)
    if log:
        ax.set_yscale("log")
        ax.set_xscale("log")
#     if display_stats is not None:
#         mean  = np.var(np.array(list(degree_distribution.values())))
#         var  = np.mean(np.array(list(degree_distribution.values())))
        #plt.gcf().text(0.9, 0.8, f"mean = {mean} \n var = {var}", fontsize=14) #, xy=(0.005, 700), xytext=(0.005, 700)
    plt.show()







def power_law_plot(view, which = None, log = True,linear_binning = False, bins = 90, draw= True,x_min = None,rounding = 2):
    if which is not None:
        values = [obj[which] for obj in view]
    else:
        values = list(view.values()) #degree
    
    #powerlaw does not work if a bin is empty
    #sum([1 if x == 0 else 0 for x in list(degree)])
    corrected_values = [x for x in values if x != 0 ]
    if x_min is not None:
        corrected_values = [x  for x in corrected_values if x>x_min]
    # fit powerlaw exponent and return distribution
    pwl_distri=pwl.pdf(corrected_values, bins = bins)
    
    if draw:
        
        rounded_values = [round(value,rounding ) for value in values]
        
        distribution = Counter(rounded_values)

        # Degree distribution
        x=[]
        y=[]
        for i in sorted(distribution):   
            x.append(i)
            y.append(distribution[i]/len(view) ) #/len(view) 
        #plot our distributon compared to powerlaw
        
        #plt.figure(figsize=(10,7))
        plt.yscale('log')
        plt.xscale('log')

        plt.xticks(fontsize=15)
        plt.yticks(fontsize=15)

        plt.xlabel('$x$', fontsize=16)
        plt.ylabel('$P(x)$', fontsize=16)
        #plt.axis((10**(-4),10**3,10**(-5),10**(-4)))
        plt.axis("auto")
        plt.plot(x,y,'ro')

#         if linear_binning:
#             pwl.plot_pdf(corrected_values, linear_bins=True, color='black', linewidth=2)
#         else:
#             pwl.plot_pdf(corrected_values, color='black', linewidth=2)
    
    return pwl_distri





# def get_activity_view(users_objs,w):
#     now = datetime.utcnow().timestamp()
#     activity_view = {obj["user_id"]:(w[0]*float(obj["statuses_count"])+w[1]*float(obj["favourites_count"])+w[2]*float(obj["friends_count"]))/((now-datetime.strptime(obj["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())/(60*60*24)) for obj in users_objs}
#     mean = np.mean(np.array(list(activity_view.values())))
#     var  = np.var(np.array(list(activity_view.values())))
#     return (activity_view,mean,var)



def sample_followers_activity(user_objs,w,sample_size):
    sample = random.sample(user_objs.tolist(),sample_size )
    now = datetime.utcnow().timestamp()
    sample = [{"user_id":int(obj["user_id"]), "followers_count":int(obj["followers_count"]), "activity":(w[0]*float(obj["statuses_count"])+w[1]*float(obj["favourites_count"])+w[2]*float(obj["friends_count"]))/((now-datetime.strptime(obj["created_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())/(60*60*24)) } for obj in sample ]
    return np.array(sample)




### Centrality Metrics 

##### Get Centralitie
def get_centrality(G, type_centrality, **kwargs):
    
    if type_centrality=="degree":
        centrality=[]
        for i in G.nodes():
            centrality.append([G.degree(i),i])
        centrality=sorted(centrality,reverse=True)
        return centrality
        
    elif type_centrality=="closeness":
        l=nx.closeness_centrality(G)
        centrality=[]
        for i in G.nodes():
            centrality.append([l[i],i])
        centrality=sorted(centrality,reverse=True)
        return centrality
    
    elif type_centrality=="betweenness":
        l=nx.betweenness_centrality(G, **kwargs)
        centrality=[]
        for i in G.nodes():
            centrality.append([l[i],i])
        centrality=sorted(centrality,reverse=True)
        return centrality
    
    elif type_centrality=="eigenvector":
        l=nx.eigenvector_centrality(G, max_iter=1000, tol=1e-06)
        centrality=[]
        for i in G.nodes():
            centrality.append([l[i],i])
        centrality=sorted(centrality,reverse=True)
        return centrality
    
    elif type_centrality=="katz":
        l=nx.katz_centrality(G, alpha=0.001, beta=1.0, max_iter=1000, tol=1e-06)
        centrality=[]
        for i in G.nodes():
            centrality.append([l[i],i])
        centrality=sorted(centrality,reverse=True)
        return centrality
    
    elif type_centrality=="pagerank":
        l=nx.pagerank(G,0.85,**kwargs)
        centrality=[]
        for i in G.nodes():
            centrality.append([l[i],i])
        centrality=sorted(centrality,reverse=True)
        return centrality
    
    elif type_centrality=="random":
        
        centrality=[]
        for i in G.nodes():
            centrality.append([i,i])
        rand.shuffle(centrality)
        return centrality

    
    elif type_centrality == "load":
        l = nx.load_centrality(G, weight = "weight")
        centrality=[]
        for i in G.nodes():
            centrality.append([l[i],i])
        #rand.shuffle(centrality)
        return centrality
    else:
        return 0
    
    

    
##### Plot Centrality Distributions
def plot_centrality_distribution(G, list_centrality, color, n_bins):
    
    dict_centrality={}
    for i in list_centrality:
        if i[0]>0.:
            dict_centrality[i[1]]=i[0]
       
    centrality_binned=log_bin(dict_centrality,n_bins)

    # we then plot their binned distribution
    x_centrality=[]
    y_centrality=[]
    for i in centrality_binned:
        x_centrality.append(i[0])
        y_centrality.append(i[1])

    plt.plot(x_centrality,y_centrality, color=color,linewidth=1.1, marker="o",alpha=0.55) 
    plt.yscale('log')
    plt.xscale('log')
    plt.xlabel('$x$', fontsize = 15)
    plt.ylabel('$P(x)$', fontsize = 15)
    plt.xticks(fontsize=12)
    plt.yticks(fontsize=12)
    plt.show()
    
    
    

        
        
        
    
def get_assortativity(H, mode, x_log = False,y_log = False, direction = "both", extremists_tolerance = None, outliers_tolerance = None):
    G = copy.deepcopy(H)
    avg_attr = defaultdict(list)
    x = []
    y = []
    attributes_dict = nx.get_node_attributes(G,mode)
    #attributes_dict = {pair[0]:pair[1] for pair in zip(attributes_dict.keys(),attributes_dict.values()) if pair[1] is not None}
    #print(attributes_dict[1184740728133607424])
    
    if extremists_tolerance is not None:
        values  = np.array([value for value in  attributes_dict.values() if value is not None])
        #print(values)
        var = np.var(values)
        #print(math.sqrt(var))
        mean = np.mean(values)
        #print(mean)
        #print(len(G.nodes()))
        #attributes_dict_notNone = {pair[0]:pair[1] for pair in zip(attributes_dict.keys(),attributes_dict.values()) if pair[1] is not None}
        removed_nodes = [pair[0]  for pair in zip( list(attributes_dict.keys()),list(attributes_dict.values())) if pair[1] is not None and abs(pair[1]-mean) > extremists_tolerance*math.sqrt(var)]
        #print(len(removed_nodes))
        attributes_dict = {pair[0]:pair[1] for pair in zip( list(attributes_dict.keys()),list(attributes_dict.values())) if pair[1] is not None and abs(pair[1]-mean) <= extremists_tolerance*math.sqrt(var)}
        #print(attributes_dict)
        G.remove_nodes_from(removed_nodes)
        #print(len(G.nodes()))
        
    if nx.is_directed(G):
        def both(j):
            a = list(G.successors(j))
            b = list(G.predecessors(j))
            a.extend(b)
            return a
    else:
        def both(j):
            a = list(G.neighbors(j))
            return a
    
    
    
    if direction == "successor":
        neighbors = G.successors
    elif direction  == "predecessor":
        neighbors = G.predecessors
    elif direction == "both":
        neighbors = both
    
    for n in G.nodes():
        succ_attr = 0
        #print([node for node in attributess_dict.keys()].index(n))
        try:
            attribute = attributes_dict[n] #[node for node in attributes_dict.keys()].index()
        except KeyError:
            continue
            
        for j in neighbors(n): #G.successors(n)
            try:
                succ_attr += attributes_dict[j] #[node for node in attributes_dict.keys()].index(j)
            except KeyError:
                continue

        #x.append(n)
        if nx.is_directed(G):
            total_neighbors = len(list(G.successors(n)))
            if total_neighbors != 0:
                avg_attr[attribute].append(succ_attr/total_neighbors)
                x.append(attribute)
                y.append(succ_attr/total_neighbors)
            else:
                avg_attr[attribute].append(0)
                x.append(attribute)
                y.append(0)
        else:
            total_neighbors = len(list(G.neighbors(n)))
            if total_neighbors != 0:
                avg_attr[attribute].append(succ_attr/total_neighbors)
                x.append(attribute)
                y.append(succ_attr/total_neighbors)
            else:
                avg_attr[attribute].append(0)
                x.append(attribute)
                y.append(0)
        
                
    
    if outliers_tolerance is not None:
        std = math.sqrt(np.var(y))
        mean  = np.mean(y)
        dct = {key:value for (key,value) in zip(x,y)}
        #print(dct)
        inlier_dct = {pair[0]:pair[1] for pair in zip( dct.keys(),dct.values()) if pair[1] is not None and abs(pair[1] - mean) <= outliers_tolerance*std}
        x = list(inlier_dct.keys())
        y = list(inlier_dct.values())
    
    attribute_assortativity = {i:np.mean(avg_attr[i]) for i in sorted(list(avg_attr.keys()))}
    #print(np.array(x).shape, np.array(y).shape)
    extrema = [min(x)-25,max(x)+25,min(y)-25,max(y)+25]
        # = [i for i in avg_attr.keys() for j in len(avg_attr[i]) ]
        
    plt.figure(figsize=(10,7))
    #plt.scatter(x,y,label=mode +'$_{nn,i}$')
    sns.regplot(x,y, robust = False,label=mode +'$_{nn,i}$')
    #plt.hlines(k_unc, 0, 500, colors='green', linestyles='solid', label='$op^{unc}_{nn}$', data=None)
    #plt.plot(sorted(attribute_assortativity.keys()), list(attribute_assortativity.values()),'r-', label='$op_{nn}(op)$') #z
    #plt.plot(list(dict(knn_avg4).keys()), list(dict(knn_avg4).values()),'r-', label='$k_{nn}(k)$') #z
    #plt.plot(sorted(avg_knn.keys()), z1,'g-')
    plt.legend(loc = 'upper left', fontsize = 15)
    plt.xlabel('$k_i$', fontsize=18)
    plt.ylabel('$k_{nn}$', fontsize=18)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    if x_log:
        plt.xscale('log')
    if y_log:
        plt.yscale('log')

    plt.title(mode + ' Assortativity Analysis', fontsize = 17)
    plt.axis(extrema)
        
    if mode == "degree":
        undirected_degree_distribution = dict(G.degree(weight = "weight"))
        degree_distrib = {k:sum([1 if k == undirected_degree_distribution[i] else 0 for i in undirected_degree_distribution.keys()])/len(G) for k in np.unique(list(undirected_degree_distribution.values()))}
        degrees = list(degree_distrib.keys())
        probs = list(degree_distrib.values())
        #k_unc = <k^2>/<k>
        k_unc = sum([(degrees[k]**2)*probs[k] for k in range(len(degrees))])/sum([(degrees[k])*probs[k] for k in range(len(degrees))])
        print("k_unc = ", k_unc)
        plt.hlines(k_unc, extrema[0], extrema[1], colors='green', linestyles='solid', label='$k^{unc}_{nn}$', data=None)
            
    #plt.axis([0.1,600,1,270])
    plt.show()
    
    
def zip_dict(dct):
    return zip(dct.keys(),dct.values())
    
    
    
def propagate_opinion(H,times = 1, weight = 0.1):
    iteration = 1
    G = copy.deepcopy(H)
    
    while iteration <= times:
        opinions_dct = nx.get_node_attributes(G,"opinion")
        inferred_opinions_dct= copy.deepcopy(opinions_dct)
    
        for n in G.nodes():
            n_opinion =opinions_dct[n]

            if n_opinion is None:
                continue

            #inferred_opinions_dct
            for j in G.predecessors(n):
                if opinions_dct[j] is None:
                    inferred_opinions_dct[j] = weight*G.get_edge_data(j,n)["weight"]*n_opinion
                elif opinions_dct[j] is not None and iteration == times  :
                    inferred_opinions_dct[j] += weight*G.get_edge_data(j,n)["weight"]*n_opinion
                    
        
        print("Nones before",iteration,"propagation: ",sum([1 if node is None else 0 for node in opinions_dct.values() ]), "total opinon= ", sum([value for value in opinions_dct.values() if value is not None]))
        print("Nones after",iteration,"propagation: ",sum([1 if node is None else 0 for node in  inferred_opinions_dct.values() ]),"total opinon= ",sum([value for value in inferred_opinions_dct.values() if value is not None]))
        nx.set_node_attributes(G, {user[0]:user[1] for user in zip_dict(inferred_opinions_dct)},"opinion")
                    
        iteration += 1
       
    return G



### Hashtags utilities

# questa è la classe che si occupa di tutto
# che nome ultra-noiso
# niente torna pure ai tuoi devices, io capisco input utente. display_and_polarize
class hashtag_annotator(): 
    def __init__(self,who , tweets_path,save_path, backup_path, max_print = 50):
        
        print("#######################################",
     "\nWELCOME TO THE HASHTAGS ANNOTATOR 1.0!",
     "\n\nThanks for choosing our product instead of prodigy, and remember that for every question, complaint or usage assistance you may email me at claudio.moroni@edu.unito.it.",
     "\nGet in contact with other life-changing technologies at https://github.com/InPhyT/inphyt.github.io."
     "\nHave fun!!!",
     "\n\nInPhyT",
     "\n#######################################")

        print("\nINSTRUCTIONS:",
             "\n\nYou will be prompted to enter the session target, which is the number of hashtags you plan to do during the current session (maybe it helps productivity).",
             "\nThen the application will be launched. In the top section of the output there will be some info like the current hashtag and below you will read all the tweets that contain the current hashtag.",
             "\nAt the bottom of the output, you will be prompted to insert the hashtag polarity.",
              "\nIf in the same input bar you enter 'settings', you will be able to modify some parameters like 'max_print' (set maximum number of tweet printed) , 'session_taget' (reset the session target), 'back' (reconsider last hashtag) and 'return' (go back to the annotator without changes) , or to quit using 'save and quit' and following the subsequent instructions.") 
        self.who = who
        self.save_path = save_path + "hashtags_"+who+".txt"
        self.backup_path  = backup_path + "hashtags_"+who+"_backup.txt"
    
        self.info_save_path = save_path+"info.txt"
        self.info_backup_path = backup_path+"info.txt"
        
        #  load hashtags
        file=open(self.save_path, "r")
        contents=file.read()
        self.hashtags_polarizations=ast.literal_eval(contents)
        file.close()
        #print(hashtags[1])
        

        self.hashtags = [dct["hashtag"] for dct in self.hashtags_polarizations ]


        
        # load info.txt
        try:
            with open(self.info_save_path, "rb") as f:
                self.info  = pickle.load(f)
                f.close()
        except FileNotFoundError as e:
            self.info = {"last_hashtag": self.hashtags[0], "completed":0 }
        
        # load tweets
        with open(tweets_path, "rb") as f:
            self.tweets = pickle.load(f)
            f.close()
        
        self.max_print  = max_print
        self.session_target = self.parse_input("What is your session target?",list(range(len(self.hashtags_polarizations))))
        print("target set to ",self.session_target )
        

        self.i = self.hashtags.index(self.info["last_hashtag"])
        self.start = self.i 


            
            
    def parse_input(self,message, allowed_values):
        while True:
            value = input(message)
            if value in {str(i) for i in allowed_values}:
                return value
            else:
                if len(allowed_values)<10:
                    print("input must be in", allowed_values)
                else:
                    print("input must be within", allowed_values[0],"-",allowed_values[-1])
                    
                    
    def save(self, hashtag_path, info_path):
        with open(hashtag_path,"wt") as f:
            f.write(str(self.hashtags_polarizations).replace("},","},\n"))
            f.close()

        with open(info_path,"wb") as f:
            pickle.dump({"last_hashtag":self.hashtags[self.i],"completed":self.i},f)
            f.close()
            
        
    def display_and_polarize(self):
        clear_output()
#         if select is not None and step is not None:
#             warnings.warn("WARNING: because select in not None, step will be ignored. Consider not specifying both of them at the same time to avoid ambiguities.")
        
        # identify tweets taht use the current hashtag
        tweets = [tweet["text"] for tweet in self.tweets if self.hashtags[self.i] in tweet["hashtags"]]
        print("##################################","\n\ncurrent hashtag = #"+ self.hashtags[self.i], "\nNumber of tweets that contain the hashtag = ", len(tweets),"(",self.max_print,")","\nsession_target = ",self.i-self.start,"/",self.session_target, "\ntotal completion:",self.i,"/",len(self.hashtags),"\n\n##################################\n\n", flush = True)
        print("TWEETS CONTAINING #"+self.hashtags[self.i],":\n\n")
        for tweet in tweets[:self.max_print]:
            print(tweet,"\n/---------/",flush = True)
            
        polarity = self.parse_input("\n\n Please specify the polarity {0,1,-1}, or access the settings by typing 'settings' : ", ["0","1","-1","settings"])

        if polarity in ["0","1","-1"]:
            polarity  = int(polarity)

            #self.hashtags_polarizations[self.hashtags[self.i]] = polarity
            self.hashtags_polarizations[next(i for i, item in enumerate(self.hashtags_polarizations) if item["hashtag"] == self.hashtags[self.i])]["polarity"] = polarity
            
            self.save(self.save_path,self.info_save_path)
        

            self.i += 1
            #j += 1

        
        elif polarity == "settings":

            what = self.parse_input("what parameter would you like to change? Must be one of {max_print, session_target, return, back, save and quit}",["max_print", "session_target", "return", "back", "save and quit"] )
            if what == "max_print":
                self.max_print = int(self.parse_input("please specify the maximum number of tweets you would like to be displayed",list(range(75))))
            elif what == "session_target":
                self.session_target = int(self.parse_input("Please set new session target", list(range(len(self.hashtags)))))
            elif what == "return":
                pass
            elif what == "back":
                self.i -= 1
            elif what == "save and quit":
                clear_output()
                
                self.save(self.save_path,self.info_save_path)

                flag = self.parse_input("Please open the hashtags file located in "+self.save_path+" to check for possible errors. If you believe there are not, enter Y to also make a backup of your current work, else enter N to keep the previous version of the above file in the backup folder as it was before this session.",["Y","N"])
                if flag == "Y":
                    self.save(self.backup_path,self.info_backup_path)
                
                #print("Bye Bye. Come back soon!!")
                clear_output()
                score = self.parse_input("bye bye, we hope to see you back soon. Please rate your user experience from 1 to 5",[1,2,3,4,5])
                clear_output()
                print("Thank you,", self.who,"!!")
                return
                

        
        
        clear_output(wait = True)
        self.display_and_polarize()
