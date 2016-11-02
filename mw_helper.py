import pycurl
import sqlite3
import threading
import time
from io import BytesIO

import certifi
from bs4 import BeautifulSoup

mw_url = 'https://microworkers.com/'
cookie = "data/cookie.txt"
db_path = "data/mw_helper.db"

class Logger():

    def __init__(self):
        self.conn = sqlite3.connect(db_path)

    def write_log(self, text, error=0):
        c = self.conn.cursor()
        c.execute("insert into log values (NULL,?,?)", (text,error))
        self.conn.commit()

    def clear_log(self):
        c = self.conn.cursor()
        c.execute("delete from log")
        self.conn.commit()


class AccountBalance(threading.Thread):

    _running = True
    conn = None

    def run(self):
        try:
            self.conn = sqlite3.connect(db_path)
        except sqlite3.Error:
            print("Error connecting to DB...")

        while(self._running):
            self.update()

    def update(self):
        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(pycurl.CAINFO, certifi.where())
        c.setopt(pycurl.COOKIEFILE, cookie)
        c.setopt(pycurl.URL, mw_url + "withdraw_new.php")
        c.setopt(pycurl.WRITEDATA, buffer)
        c.setopt(pycurl.FOLLOWLOCATION, True)
        c.perform()
        c.close()

        body = buffer.getvalue()

        body = BeautifulSoup(body, "html.parser")
        balance = body.findAll('div', {'class':'methodlistcol02'})[4].find('p').contents[0]

        c = self.conn.cursor()
        try:
            c.execute("update user set balance = ?", (balance,))
        except sqlite3.OperationalError:
            print("Database locked...")
        self.conn.commit()
        time.sleep(4)


class MWHelper(threading.Thread):

    conn = None
    db_path = db_path
    _running = True

    def run(self):
        try:
            self.conn = sqlite3.connect(db_path)
        except sqlite3.Error:
            print("Error connecting to DB...")

        self.clear_jobs()
        self.connect_to_mw()
        acc_balance = AccountBalance()
        acc_balance.start()
        while self._running:
            self.extract_jobs()
            time.sleep(9)

        self.clear_jobs()
        acc_balance._running = False

    def extract_jobs(self):
        page = 'jobs.php?Sort=COST&Filter=no&Id_category=ALL'

        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(pycurl.CAINFO, certifi.where())
        c.setopt(pycurl.COOKIEFILE, cookie)
        c.setopt(pycurl.URL, mw_url + page)
        c.setopt(pycurl.WRITEDATA, buffer)
        c.setopt(pycurl.FOLLOWLOCATION, True)
        c.perform()
        c.close()

        body = buffer.getvalue()
        body = BeautifulSoup(body, "html.parser")

        jobs = []
        joblistarea = body.find('div', attrs={'class':'joblistarea'})
        js = joblistarea.findAll('div', attrs={'class':'jobslist'})

        c = self.conn.cursor()

        for j in js:
            job_name = j.find('div', attrs={'class':'jobname'}).find('a').contents[0]
            job_pay  = j.find('div', attrs={'class':'jobpayment'}).find('p').contents[0]
            job_url  = j.find('a')['href']
            if "http" not in job_url:
                job_url = mw_url + job_url
            jobs.append((job_name, job_pay, job_url, 0))

        old_jobs = self.get_jobs()
        jobs = set(jobs) - set(old_jobs)
        try:
            c.executemany('insert or ignore into jobs values (NULL,?,?,?,?)', jobs)
        except sqlite3.OperationalError:
            print("Database locked...")
        self.conn.commit()

    def get_jobs(self):
        c = self.conn.cursor()
        jobs = c.execute('select * from jobs').fetchall()
        return jobs

    def clear_jobs(self):
        print("Clearing jobs...")
        c = self.conn.cursor()
        c.execute("delete from jobs")
        self.conn.commit()


    def connect_to_mw(self):
        host_url = "https://microworkers.com/login.php"
        fields = "Email=c.lomax.uk%2Bmicroworker%40gmail.com&Password=RpNF6YoOergaOp52ZyHZ&Button=Login"

        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(pycurl.CAINFO, certifi.where())
        c.setopt(pycurl.COOKIEFILE, cookie)
        c.setopt(pycurl.COOKIEJAR, cookie)
        c.setopt(pycurl.URL, host_url)
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.POSTFIELDS, fields)
        c.setopt(pycurl.WRITEDATA, buffer)
        c.setopt(pycurl.FOLLOWLOCATION, True)

        print("Connecting to MW...")

        c.perform()
        c.close()

        print("Connected to MW...")
