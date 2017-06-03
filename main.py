#!/usr/bin/python3

from tkinter import *
from tkinter import ttk
from mw_helper import MWHelper
import webbrowser
import sqlite3
import subprocess

TITLE_FONT = ("Helvetica", 12, "bold")
LIST_ITEM_FONT = ("Helvetica", 12)
STATUSBAR_FONT = ("Helvetica", 10)

def send_message(message):
	subprocess.Popen(['notify-send', message])
	return

class MWHelperGUI(Tk):

    new_jobs = 0

    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.wm_title("Microworkers Helper")

        self.default_bg = self.cget('bg')

        nav_menu = Frame(self)
        nav_menu.pack(side=TOP, fill=X)

        self.jobs_button = Button(nav_menu, text="Jobs", font=TITLE_FONT, command=lambda: self.show_frame("Jobs"))
        filter_button = Button(nav_menu, text="Filter", font=TITLE_FONT, command=lambda: self.show_frame("Filter"))
        settings_button = Button(nav_menu, text="Settings", font=TITLE_FONT, command=lambda: self.show_frame("Settings"))
        account_balance_label = AccountBalanceLabel(parent = nav_menu, controller=self)
        account_balance_label.pack(side=RIGHT)

        self.jobs_button.pack(side=LEFT)
        filter_button.pack(side=LEFT)
        settings_button.pack(side=LEFT)

        statusbar = Frame(self)
        statusbar.pack(side=BOTTOM, fill=X, expand=FALSE)
        statusbar.configure(height=30)
        statusbar.grid_rowconfigure(2, weight=1)
        statusbar.grid_columnconfigure(0, weight=1)

        status_label = StatusbarLabel(parent=statusbar, controller=self)
        status_label.pack(side=LEFT)

        container = Frame(self)
        container.pack(side=TOP, fill=BOTH, expand=True)
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        for F in (Jobs, Filter, Settings):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=1, column=0, sticky=NSEW)

        self.update()
        self.show_frame("Jobs")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

    def update(self):
        num_jobs = self.frames["Jobs"].get_jobs_list_length()
        if num_jobs > 0:
            self.jobs_button.config(bg="red")
            if (self.new_jobs < num_jobs):
                self.new_jobs = num_jobs
                send_message("New microworkers job!")
                #winsound.PlaySound('data/new_job.wav', winsound.SND_FILENAME)

        else:
            self.new_jobs = 0
            self.jobs_button.config(bg=self.default_bg)
        self.after(1000, self.update)


class StatusbarLabel(Label):

    def __init__(self, parent, controller):
        Label.__init__(self, parent, text="", font=STATUSBAR_FONT, padx=5, pady=5)
        self.update()

    def update(self):
        self['text'] = self.get_last_message()
        self.after(1000, self.update)

    def get_last_message(self):
        c = conn.cursor()
        msg = c.execute('select * from log where id=(select max(id) from log)').fetchone()[1]
        return msg


class AccountBalanceLabel(Label):

    url = "https://microworkers.com/withdraw_new.php"

    def __init__(self, parent, controller):
        Label.__init__(self, parent, text="$--.--",  font=TITLE_FONT, padx=5)
        self.parent = parent
        self.bind("<Button-1>", lambda e: open_url(self.url))
        self.controller = controller
        self.update()

    def update(self):
        self['text'] = self.get_balance()
        self.after(1000, self.update)

    def get_balance(self):
        c = conn.cursor()
        balance = c.execute('select * from user').fetchone()[0]
        return balance


class Jobs(Frame):

    jobs = []
    jobs_list_headings = ["ID","Name", "Pay", "URL"]

    def __init__(self, parent, controller):
        Frame.__init__(self, parent, pady=10, padx=10)
        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.jobs_list = ttk.Treeview(self, columns=self.jobs_list_headings, show="headings")
        self.jobs_list.grid(column=0, row=0, sticky=NSEW, in_=self)
        self.jobs_list.column("#1", minwidth=0, width=0, stretch=NO)
        self.jobs_list.column("#2", minwidth=100, width=400, stretch=NO)
        self.jobs_list.column("#3", minwidth=100, width=100, stretch=NO)

        self.jobs_list.bind("<Double-1>", self.on_double_click)
        self.jobs_list.bind("<Button-2>", self.hide_job)

        ysb = ttk.Scrollbar(self, orient=VERTICAL, command=self.jobs_list.yview)
        self.jobs_list['yscroll'] = ysb.set
        ysb.grid(in_=self, row=0, column=1, sticky=NS)

        sortby(self.jobs_list, "Pay", 0)

        self.update()

    def hide_job(self, event):
        item = self.jobs_list.item(self.jobs_list.selection())
        try:
            id = item["values"][0]
        except IndexError:
            print("No job selected...")

        c = conn.cursor()
        try:
            jobs = c.execute("update jobs set hidden=1 where id=?", (id,))
        except sqlite3.OperationalError:
            print("Database locked...")
        except UnboundLocalError:
            pass
        conn.commit()
        self.update()

    def update(self):
        for i in self.jobs_list.get_children():
            self.jobs = []
            self.jobs_list.delete(i)

        for h in self.jobs_list_headings:
            self.jobs_list.heading(h, text=h.title(), command=lambda c=h: sortby(self.jobs_list, c, 0))

        _jobs = self.get_jobs()

        for j in _jobs:
            if not j[4] and self.is_job_wanted(j[1]):
                self.jobs.append(j)
                self.jobs_list.insert('', 'end', values = j)

        sortby(self.jobs_list, "Pay", 1)

        self.controller.after(20000, self.update)

    def is_job_wanted(self, job_name):
        is_wanted = False
        c = conn.cursor()
        wanted_jobs = list(c.execute('select * from filter').fetchall())
        if len(wanted_jobs) > 0:
            for w in wanted_jobs:
                if w[1].lower() in job_name.lower():
                    is_wanted = True
        else:
            is_wanted = True

        return is_wanted

    def get_jobs_list_length(self):
        return len(self.jobs)

    def get_jobs(self):
        c = conn.cursor()
        jobs = c.execute('select * from jobs').fetchall()
        return jobs

    def on_double_click(self, event):
        item = self.jobs_list.item(self.jobs_list.selection())
        open_url(item["values"][3])


class Filter(Frame):

    wanted = []
    filter_list_headings = ["ID", "Filter"]

    def __init__(self, parent, controller):
        Frame.__init__(self, parent, pady=10, padx=10)
        self.controller = controller

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.add_filter_entry = Entry(self)
        self.add_filter_entry.grid(in_=self,row=0,column=0,sticky=NW,padx=10)

        self.add_filter_button = Button(self, text="Add")
        self.add_filter_button.grid(in_=self,row=0,column=0,sticky=NE)
        self.add_filter_button.bind("<Button-1>", self.on_click)

        self.filter_list = ttk.Treeview(self, columns=self.filter_list_headings, show="headings")
        self.filter_list.grid(in_=self,row=1,column=0,sticky=NSEW)
        self.filter_list.column("#1", minwidth=0, width=0, stretch=NO)
        self.filter_list.column("#2", minwidth=100, width=400, stretch=YES)
        self.filter_list.bind("<Button-2>", self.hide_filter)

        ysb = ttk.Scrollbar(self, orient=VERTICAL, command=self.filter_list.yview)
        self.filter_list['yscroll'] = ysb.set
        ysb.grid(in_=self, row=1, column=1, sticky=NS)

        self.update()

    def update(self):
        c = conn.cursor()
        self.wanted = c.execute("select * from filter").fetchall()

        for i in self.filter_list.get_children():
            self.filter_list.delete(i)

        for w in self.wanted:
            self.filter_list.insert('', 0, values=w)

    def on_click(self, event):
        c = conn.cursor()
        c.execute("insert or ignore into filter values (NULL, ?)", (self.add_filter_entry.get(),))
        conn.commit()
        app.frames["Jobs"].update()
        self.update()

    def hide_filter(self, event):
        selection = self.filter_list.selection()
        value = self.filter_list.item(selection)["values"]
        c = conn.cursor()
        c.execute("delete from filter where id=?", (value[0],))
        conn.commit()
        self.update()



class Settings(Frame):

    def __init__(self, parent, controller):
        Frame.__init__(self, parent, pady=10, padx=10)
        self.controller = controller

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)



def sortby(list, col, descending):
    data = [(list.set(child, col), child) for child in list.get_children('')]
    data.sort(reverse=descending)
    for ix, item in enumerate(data):
        list.move(item[1], '', ix)
        list.heading(col, command=lambda col=col: sortby(list, col, int(not descending)))

def open_url(url):
    webbrowser.open(url)

def on_close():
    mw_helper._running = False
    app.destroy()

if __name__ == "__main__":
    mw_helper = MWHelper()
    mw_helper.start()

    conn = sqlite3.connect(mw_helper.db_path)

    app = MWHelperGUI()
    app.minsize(width=680, height=480)
    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()

