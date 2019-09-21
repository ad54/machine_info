#
# Python script to fetch system information
# Author -  Agam
# Tested with Python3 and Python2 on windows 7,10 64-32 bit
#

from __future__ import print_function
import sys
import time
import threading
import logging
import re
import platform
import uuid
import pandas as pd
import datetime
import socket
import psutil
from datetime import timedelta
logging.basicConfig(filename='log.txt',
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%a, %d %b %Y %H:%M:%S',
                            level=logging.ERROR)
elastic_url = ''
elastic_username = ''
elastic_password = ''
from_email_id = ''
from_email_pass = ''
to_email_id = ''

def run_data():
    class Spinner:
        busy = False
        delay = 0.1

        @staticmethod
        def spinning_cursor():
            while 1:
                for cursor in '|/-\\': yield cursor

        def __init__(self, delay=None):
            self.spinner_generator = self.spinning_cursor()
            if delay and float(delay): self.delay = delay

        def spinner_task(self):
            while self.busy:
                sys.stdout.write(next(self.spinner_generator))
                sys.stdout.flush()
                time.sleep(self.delay)
                sys.stdout.write('\b')
                sys.stdout.flush()

        def start(self):
            self.busy = True
            threading.Thread(target=self.spinner_task).start()

        def stop(self):
            self.busy = False
            time.sleep(self.delay)



    # Get MAC address
    mac_address = (hex(uuid.getnode())).replace('L','')
    print('your mac_address : ', mac_address)

    # Get Local IP address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))  # connect() for UDP doesn't send packets
    local_ip_address = s.getsockname()[0]
    print('your local_ip_address : ', local_ip_address)


    fromaddr = from_email_id
    password = from_email_pass

    email_id = to_email_id
    name_of_developer = ''


    # Connect elasticsearch DB
    machine_details_table = 'machine_details'
    process_details_table = 'process_details'
    disk_details_table = 'disk_details'

    from elasticsearch import Elasticsearch

    es = Elasticsearch([elastic_url],
                       http_auth=(elastic_username, elastic_password))
    es.indices.create(index = machine_details_table, ignore=400)
    es.indices.create(index = process_details_table, ignore=400)
    es.indices.create(index = disk_details_table, ignore=400)

    spinner = Spinner()
    print('process is going on...', end='')
    spinner.start()

    run_status = 'pending'
    timestamp = datetime.datetime.now() - timedelta(hours=5, minutes=30)
    tstamp = datetime.datetime.today().strftime('%Y:%m:%d_%H:%M:%S')
    mac_date = str(mac_address) + '_' + str(tstamp)


    # For Sending mail
    def send_mail(alert_type, args):
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders

        try:
            # fromaddr = 'alerts.xbyteio@gmail.com'
            toaddr = email_id.split(',')

            msg = MIMEMultipart()

            msg['From'] = fromaddr
            msg['To'] = ",".join(toaddr)
            msg['Subject'] = str(local_ip_address) + " Machine info :"

            if alert_type == 1:
                body = 'Respected Sir/Madam, \n\n In the system : ' + str(local_ip_address) + ' , Used By : ' + str(
                    name_of_developer) + '.\n Available memory is only : ' + str(args) + ' %  ( ' + str(
                    hdd_available) + ' of ' + str(
                    hdd_total) + ' ) \n Please take care of it.'
            elif alert_type == 2:
                body = 'Respected Sir/Madam, \n\n In the system : ' + str(local_ip_address) + ' , Used By : ' + str(
                    name_of_developer) + '.\n  : ' + str(args) + ' service is not running  \n Please take care of it.'
            elif alert_type == 3:
                body = 'Respected Sir/Madam, \n\n In the system : Used By ' + str(local_ip_address) + ' , Used By : ' + str(
                    name_of_developer) + '.\n : Following new processes found \n(' + str(
                    args) + ') \n Please take care of it. you can add valid process in the following sheet' \
                            '  \n:https://docs.google.com/spreadsheets/d/1iSVwJ7doRafUlfxoQ_w66fjriDOUt_Lmfwd1Oip8Fig/edit#gid=868838991'

            msg.attach(MIMEText(body, 'plain'))

            p = MIMEBase('application', 'octet-stream')
            s = smtplib.SMTP('smtp.gmail.com', 587)
            s.starttls()
            s.login(fromaddr, password)
            text = msg.as_string()
            # sending the mail
            s.sendmail(fromaddr, toaddr, text)
            # terminating the session
            s.quit()
            print('Email  sent')
        except Exception as e:
            print('Error in sending Mail : ' + str(e))


    drive_wise_hdd, cpu_name,os_version, system_name = '', '','',''
    current_ram_usage = available_disk_percentage = ram = hdd_available = hdd_total = cpu_utilization = no_of_prod_exe = no_of_unprod_exe = 0
    mysql_running = False
    # os_architecture
    try:
        os_architecture = platform.architecture()[0]
    except:
        os_architecture = ''
    # os
    try:
        operating_system = platform.system()
    except:
        operating_system = ''

    if run_status == 'pending':
        # Get CPU utilization
        try:
            os_version = platform.uname().release
            cpu_utilization = psutil.cpu_percent()
        except Exception as e:
            os_version = ''
            cpu_utilization = 0

        # current_ram_usage
        try:
            current_ram_usage = psutil.virtual_memory()[2]
        except:
            current_ram_usage = -1

        # MySQL service status
        mysql_running = False
        try:
            if psutil.win_service_get('MySQL56').as_dict()['status'] == 'running' or psutil.win_service_get('MySQL80').as_dict()['status'] == 'running':
                mysql_running = True
        except Exception as e:
            try:
                if psutil.win_service_get('MySQL80').as_dict()['status'] == 'running':
                    mysql_running = True
            except Exception as e:
                print(e)

        if mysql_running == False:
            send_mail(2, 'mysqld')
        # Get running Process
        try:
            system_name = platform.node()

            un_recognized_process = []
            p_df = pd.read_csv('https://docs.google.com/spreadsheets/d/1iSVwJ7doRafUlfxoQ_w66fjriDOUt_Lmfwd1Oip8Fig/export?gid=1835197844&format=csv')
            p_list = list(p_df['virus_name'])
            process_name_list = []
            prod_process_list = []
            unprod_process_list = []
            pids = psutil.pids()
            for pid in pids:
                try:
                    p = psutil.Process(pid)
                    process_name = p.name()
                    if not str(p.exe()).lower().strip().startswith('c:'):
                        prod_process_list.append(process_name)
                        process_type = 'productive'
                    else:
                        unprod_process_list.append(process_name)
                        process_type  = 'unproductive'
                    process_memory = (p.memory_info()[0]) / 10 ** 6
                    process_memory_percent = p.memory_percent()
                    process_name_list.append(process_name)

                    if process_name in p_list: un_recognized_process.append(process_name)
                    p1 = {'mac_address': mac_address,
                          'local_ip_address': local_ip_address,
                          'name_of_developer': name_of_developer,
                          'process_id': pid,
                          'process_name': process_name,
                          'process_memory': process_memory,
                          'process_memory_percent': process_memory_percent,
                          'process_type':process_type,
                          'run_date': timestamp}

                    es.index(index=process_details_table, doc_type='wmi_data', body=p1)
                except Exception as e:
                    pass
            no_of_prod_exe = len(prod_process_list)
            no_of_unprod_exe = len(unprod_process_list)
            if len(un_recognized_process) > 0:
                send_mail(3, ', '.join(un_recognized_process))
        except Exception as e:
            print((e))
            system_name = ''
            no_of_prod_exe = no_of_unprod_exe = 0


        # HDD space
        try:
            drive_data = {}
            hdd_total = 0
            hdd_available = 0
            for ps in [p.device for p in psutil.disk_partitions()]:
                try:
                    drive_name = ps[0]
                    total_disk_space = int(psutil.disk_usage(ps).total/(1024**3))
                    available_disk_space = int(psutil.disk_usage(ps).free/(1024**3))
                    available_disk_percentage = int(100 -psutil.disk_usage(ps).percent)
                    drive_data[str(drive_name)] = str(available_disk_space) + '  of ' + str(total_disk_space)
                    d1 = {'mac_address': mac_address,
                          'local_ip_address': local_ip_address,
                          'name_of_developer': name_of_developer,
                          'name_of_drive': drive_name,
                          'total_disk_space': total_disk_space,
                          'available_disk_space': available_disk_space,
                          'available_disk_percentage': available_disk_percentage,
                          'run_date': timestamp}
                    es.index(index = disk_details_table, doc_type='wmi_data', body=d1)
                    hdd_available += available_disk_space
                    hdd_total += total_disk_space
                except Exception as e:
                    logging.error('In disk details insertion : '+str(e))
            drive_wise_hdd = str(drive_data).replace('{', '').replace('}', '')
            available_disk_percentage = int(round((float(hdd_available) * 100) / hdd_total, 2))
            if int(available_disk_percentage) < 20:
                send_mail(1, available_disk_percentage)
        except:
            hdd_total = available_disk_percentage = hdd_available = 0

        # RAM
        ram = psutil.virtual_memory().total/(1024**3)
        run_status = 'done'
        cpu_name = platform.processor()
        system_name = socket.gethostname()


    # Machine details Db insertion
    try:
        e1 = {'mac_date': mac_date,
              'mac_address': mac_address,
              'os_architecture': os_architecture,
              'local_ip_address': local_ip_address,
              'operating_system': str(operating_system),
              'os_version': str(os_version),
              'name_of_developer': str(name_of_developer),
              'cpu_utilization': int(cpu_utilization),
              'system_name': str(system_name),
              'ram': int(ram),
              'current_ram_usage': int(current_ram_usage),
              'hdd_total': int(hdd_total),
              'hdd_available': int(hdd_available),
              'available_disk_percentage': int(available_disk_percentage),
              'drive_wise_hdd': str(drive_wise_hdd),
              'cpu_name': str(cpu_name),
              'run_status': str(run_status),
              'run_date': timestamp,
              'no_of_prod_exe' : no_of_prod_exe,
              'no_of_unprod_exe' : no_of_unprod_exe,
              'mysql_running': (mysql_running)
              }
        es.index(index=machine_details_table, doc_type='wmi_data', id=mac_date, body=e1)
        spinner.stop()
        print('Machine details inserted')

    except Exception as e:
        logging.error(e)

run_data()