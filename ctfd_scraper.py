# What do you think you're doing here reading code like that? There ain't any revshell here don't worry

try:
    from pathlib import *
    import argparse
    from datetime import datetime
    import re
    import os, sys
    sys.path.insert(1, str(Path(os.path.realpath(__file__)).parents[1]))
    from requests import session
    from bs4 import BeautifulSoup
except Exception as e:
    raise ImportError("Dude, install the requirements...\n" + str(e))

class MESSAGE(object):
    STATE = ("SUCCESS", "DEBUG", "INFO", "WARNING", "ERROR")


def clean_directory_name(name):
    clean_ascii = ''.join([i if ord(i) < 128 else ''for i in name])
    return ''.join(['_' if i in [' ', '\\', '/', ':', '|', '<', '>', '*', '?'] else i for i in clean_ascii]) # Restricted chars


def log(text, state=1, clean=False):  # Append information
    if "\n" in text:
        lines=[x for x in text.split("\n") if x !="" and x !="\n"]
        for text in lines:
            logline(text, state, clean)
    else:
        logline(text, state, clean)

def logline(text, state=1, clean=False):
    if not clean:
        text = "[" + datetime.now().strftime("%H:%M:%S") + "] [" + MESSAGE.STATE[state] + "] " + text
    print(text)


class Challenge:
    def __init__(self, CTF=None, args=None, file=None, text=None):
        self.solved = False
        self.files = []
        if CTF:
            if CTF.url:
                # Newly scraped => Online CTF
                self.CTF = CTF
                self.id = args['id']
                self.name = clean_directory_name(args['name'])
                self.category = clean_directory_name(args['category'].lower())
                self.directory = self.CTF.path.joinpath(self.category).joinpath(self.name)
                self.value = args['value']
                self.type = args['type']
            elif CTF.path:
                # Already scraped => Offline CTF
                self.CTF = CTF
                self.name = clean_directory_name(args['name'])
                self.category = clean_directory_name(args['category'].lower())
                self.directory = self.CTF.path.joinpath(self.category).joinpath(self.name)
        else:
            # Challenge alone
            if file:
                self.files = [file]
            self.desc = str(text) if text else "" 
            self.directory = Path.cwd().joinpath("ExcaliburOutput-" + str(datetime.now().day) + "-" +
                                                 datetime.now().strftime("%H:%M:%S").replace(":", "."))
            self.name = "log"

        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        self.notefile_path = self.directory.joinpath(self.name + '.md')

    def __str__(self):
        a=""
        a+="Challenge has "+str(len(self.files))+" files\n"
        a+="Challenge desc: "+str(self.desc)+"\n"
        a+="Challenge directory: "+str(self.directory)+"\n"
        try:
            with open(self.notefile_path,"r") as notefile:
                chars=len(notefile.read())
            a+="Challenge notefile "+str(self.notefile_path)+", it has "+str(chars)+" characters\n"
        except Exception as e:
            a+="Could,t process notefile: "+str(e)+"\n"
        return a

    def scrape(self):
        
        self.get_info()
        self.get_files()

        self.log("# "+self.name,clean=True)
        self.log("##### Challenge's type: "+self.type,clean=True)
        if self.files and len(self.files)!=0:
            self.log("### Challenge's files:",clean=True)
            for file in self.files:
                self.log(file.name,clean=True)
        self.log("##### Challenge's description: "+self.desc,clean=True)
    
        self.log("### Debug",clean=True)



    def get_info(self):
        data = self.CTF.session.get(self.CTF.challenges_url+'/'+str(self.id)).json()['data']
        self.desc=BeautifulSoup(data['description'],'lxml').text
        self.type=data['type']
        self.file_list=data['files'] #These are not pathlib paths don't use this variable please

    def get_files(self):
        for file_url in self.file_list:
            filename  = file_url.split('/')[-1].split('?')[0]
            path=self.directory.joinpath(filename)
            if not os.path.exists(path):
                try:
                    resp = self.CTF.session.get(self.CTF.url + file_url, stream=True)
                    with open(path, 'wb') as handle:
                        for chunk in resp.iter_content(chunk_size=512):
                            if chunk:
                                handle.write(chunk)
                except Exception as e:
                    log(str(e),4)
            self.files.append(Path(path))



    def load(self):
        self.files = [x for x in self.directory.glob('**/*') if '.md' not in str(x) and x.is_file()]
        with open(self.notefile_path,'r+') as notefile:
            notefile_content=notefile.read()
        try:
            self.desc=notefile_content.split("##### Challenge's description: ")[1].split("### Debug")[0]
        except:
            log("Couldn't scrap challenge's description",4)
            self.desc=""
            
        try:
            self.type=notefile_content.split("##### Challenge's type:")[1].split("\n")[0]
        except:
            log("Couldn't scrap challenge's type",4)
            self.type="None"





    def log(self, text, verbose=False, no_verbose_output=None, state=1, clean=False):  # Append information
        if "\n" in text:
            lines=[x for x in text.split("\n") if x !="" and x !="\n"]
            for text in lines:
                self.logline(text, verbose, no_verbose_output, state, clean)
        else:
            self.logline(text, verbose, no_verbose_output, state, clean)

    def logline(self, text, verbose=False, no_verbose_output=None, state=1, clean=False):
        if not clean:
            text = "[" + datetime.now().strftime("%H:%M:%S") + "] [" + MESSAGE.STATE[state] + "] " + text
            if no_verbose_output:
                no_verbose_output = "[" + datetime.now().strftime("%H:%M:%S") + "] [" + MESSAGE.STATE[state] + "] " +\
                                    no_verbose_output
        if verbose:
            print(text)
        elif no_verbose_output:
            print(no_verbose_output)
        with open(self.notefile_path, "a+") as notefile:
            notefile.write(text+"  \n")

        




class CTF():
    def __init__(self, args, base_path=None):
        
        self.url=None
        self.path=None
        if re.match(r"(https?://(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_+.~#?&/=]*)",args.ctf):
            log("This is an online CTF, initiating scrapping...",2)
            # Online CTF
            self.url = args.ctf
            # Add trailing slash
            if self.url[len(self.url)-1] !="/":
                self.url+="/"
            self.categories = []  # All lower case
            self.challenges = []
            self.challenges_id = []
            self.auth = dict(name=args.login, password=args.password)
            self.challenges_url = self.url + '/api/v1/challenges'
            self.hints_url = self.url + '/api/v1/hints'
            self.login_url = self.url + '/login'
            if self.login():
                if not base_path:
                    base_path = Path.cwd()
                self.path = base_path.joinpath(self.title)
                if not os.path.exists(self.path):
                    os.makedirs(self.path)
                self.scrape()
            else:
                log("Couldn't login to the CTF, check credentials, url and availibility",4)
                exit()
        else:
            # Offline CTF
            log("This is an offline CTF, initiating loading...",2)
            self.path=Path(args.ctf)
            self.categories=[x.name for x in self.path.glob('./*/')]
            self.challenges = []
            for challenge_path in [x for x in self.path.glob('./*/*')]:
                chall=Challenge(self,args={"name":challenge_path.name,"category":challenge_path.parents[0].name})
                chall.load()
                self.challenges.append(chall)




    def login(self):
        try:
            self.session = session()
            resp  = self.session.get(self.login_url)
            soup  = BeautifulSoup(resp.text,'lxml')
            nonce = soup.find('input', {'name':'nonce'}).get('value')
            self.auth['nonce'] = nonce
            self.title = soup.title.string
            self.session.headers.update({'User-Agent' : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0"})
            resp=self.session.post(self.login_url, data=self.auth)
            return "Forgot" not in resp.text
        except Exception as e:
            log(str(e),4)
            log("Couldn't login to the CTF, check credentials, url and availibility",4)
            exit()


    def scrape(self):
        log("Scraping the CTF...",2)
        resp=self.session.get(self.challenges_url).json()["data"]
        #print(resp)
        new=0
        for chall_info in resp:
            #We check if we didn't already scraped the challenge by checking the notefile path of the challenge
            challenge=Challenge(self,chall_info)

            if not os.path.exists(challenge.notefile_path):
                new+=1
                self.categories.append(challenge.category)
                self.categories=list(set(self.categories))

                #Check if category directory exists
                if not os.path.exists(self.path.joinpath(challenge.category)):
                    os.makedirs(self.path.joinpath(challenge.category))

                challenge.scrape() # Initiate notefile, scrape files and desc

                log("Scraped the challenge "+str(challenge.name),2)
                self.challenges.append(challenge)
                self.challenges_id.append(challenge.id)
            else:
                #If already scraped, we only GET for the desc for the info and reuse the same files => create seperate file for others? like notefile, chall files, media/ ?
                log("The challenge "+str(challenge.name)+" was already scraped and will be loaded from save.",2) 
                challenge.solved = True #Temporary

                challenge.load() # Load files and desc

                self.challenges.append(challenge)
                


        log("I found "+str(new)+" new challenges!",2)
        #print(self.challenges,self.categories)

    def update(self):
        if self.url:
            log("Looking for newly unlocked challenges",2)
            if self.login():
                self.scrape()
            else:
                log("[!] Couldn't login to the CTF, check credentials, url and availibility. This is not the first login attempt.",4)
                exit()




def main():
    parser = argparse.ArgumentParser(description='Main function for the scraper')

    parser.add_argument('--ctf', type=str,
                        help='CTFd URL or local dir')

    parser.add_argument('--login', type=str,
                        help='Login username for the CTF')
    parser.add_argument('--password', type=str,
                        help='Login password for the CTF')
    
    args = parser.parse_args()

    if not args.ctf or not args.login or not args.password:
        print("Invalid usage, try ctfd_scraper.py --help")
        exit(0)

    ctf = CTF(args)


if __name__ == '__main__':
    main()