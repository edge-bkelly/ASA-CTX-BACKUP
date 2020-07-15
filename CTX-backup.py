__author__ = "Ben Kelly"

from sys import argv
import paramiko
import re
import time
import os
from datetime import date
from pathlib import Path
import shutil
import getpass

#Sets up Paramiko SSH and sets it to automatically trust unknown keys
ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

def open_ssh(device,user,password):
    # Connect to the firewall and change to System Context
    ssh_client.connect(hostname=device,username=user,password=password)
    remote_connection = ssh_client.invoke_shell()
    remote_connection.send("ch context system\n")
    time.sleep(1)
    remote_connection.send("write memory all\n \n")
    time.sleep(5)
    remote_connection.send("terminal pager 0\n")
    time.sleep(1)

    return remote_connection

def get_contexts(connection):
    #Regular Expression to filter output to only show CFG files
    #expression = re.compile('\\S*.cfg')
    expression = re.compile(r'(?<=/)\S*.cfg')
    #Sends the show Context command and receives the output back
    connection.send("show context\n")
    time.sleep(5)
    output = connection.recv(99999).decode(encoding='utf-8')
    #Filters the output and puts the CFG names into a list
    ctx_list = expression.findall(output)

    return ctx_list

def backup_context(connection,ctx):
    #Print the current context to screen
    print(f"   Backing up {ctx}")
    #set pager to 0 so you get full output
    connection.send("config t\n")
    #time comamnds pause for x seconds to ensure command has time to run before next one is sent
    time.sleep(1)
    #sens more command so output includes passwords
    string = "more disk0:{}\n".format(ctx)
    connection.send(string)
    time.sleep(3)
    #receive the output of the more command back and put in variable
    output = connection.recv(99999).decode(encoding='utf-8')
    #Dump config out to a file
    with open(ctx,'w') as out_file:
        out_file.write(output)

def obtain_hostname (connection):
    connection.send("\n\nshow run hostname\n")
    time.sleep(1)
    host_output = connection.recv(999).decode(encoding='utf-8')
    host_regex = re.findall(r'(?<=hostname\s)\S+',host_output)
    return host_regex[0]

#Get user and firewall details
print('\n')
firewall = input('Enter the IP address of the Firewall: ')
user = input('Enter Username: ')
password = getpass.getpass(prompt='Enter password: ')
print('\n \nRunning Backup\n')

#Invoke the module to connect to the device.
firewall = open_ssh (firewall,user,password)
#Invoke the module to get the list of contexts
contexts = get_contexts(firewall)

#create the folder structure
#Check if the Backups folder exists and create if not
if not os.path.exists('Backups'):
    os.mkdir('Backups')
#Change working DIrectory to Backup Folder
os.chdir('Backups')

#Clean up old backups
#get the current time in seconds since epoch
current_time = time.time()
#compares creation time vs time now and deletes recursively if older than 7 days
for file in os.listdir():
    creation_time = os.path.getctime(file)
    if (current_time - creation_time) // (24 * 3600) >=7:
        shutil.rmtree(file)

#create a folder for todays date
folder_name = (date.today()).strftime("%d-%m-%y")
if not os.path.exists(folder_name):
    os.mkdir(folder_name)
#change in to Folder
os.chdir(folder_name)

#create a folder for the hostname of the device
#obtain the hostname
hostname = obtain_hostname (firewall)
#create folder
if not os.path.exists(hostname):
    os.mkdir(hostname)
#Change into folder 
os.chdir(hostname)

#Loop through context and back them up
for ctx in contexts:
    backup_context(firewall,ctx)

#close the connection
firewall.close()

print('\nComplete!')
