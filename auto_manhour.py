# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta
import time
import sqlite3
import requests
import random
import pytz
import json


def today_match_string(pickdate=datetime.now()):
    date_day_string = pickdate.strftime("%Y%m%dT")
    print 'prefix is %s' % date_day_string
    return date_day_string


def retrive_event_by_start_date_prefix(prefix, db_path='pyas.asdb'):
    conn = sqlite3.connect(db_path)
    curs = conn.cursor()
    sql = "SELECT ServerId, calendar_Subject, calendar_StartTime, calendar_EndTime from MSASCAL where calendar_StartTime like \"'%s%%\"" % prefix
    curs.execute(sql)
    synckeys_rows = curs.fetchall()
    events = []
    for row in synckeys_rows:
        server_id = row[0]
        rawtitle = row[1].strip("'")
        title = rawtitle.encode().decode('unicode_escape').encode("raw_unicode_escape")

        start = datetime.strptime(row[2], "'%Y%m%dT%H%M%SZ'")
        end = datetime.strptime(row[3], "'%Y%m%dT%H%M%SZ'")

        duration = end - start
        mins = duration.total_seconds() / 60
        print title
        #
        start = start + timedelta(hours=8)
        events.append({
            "uuid": server_id,
            "title": title,
            "start_at": start,
            "duration_mins": mins
        })
    # print "events:", events
    conn.close()
    return events


def init_kv_db(db_path='pyas.asdb'):
    conn = sqlite3.connect(db_path)
    curs = conn.cursor()
    try:
        curs.execute("""CREATE TABLE AutoManhourKeyValue (Key text, Value text)""")
        indicies = ['CREATE UNIQUE INDEX "main"."AutoManhourKeyValue_Key_Idx" ON "AutoManhourKeyValue" ("Key" ASC)',]
        for index in indicies:
            curs.execute(index)
    except sqlite3.OperationalError as e:
        if e.message != "table AutoManhourKeyValue already exists":
            raise e
    conn.commit()
    conn.close()


def get_manhour_keyvalue(key, path="pyas.asdb"):
    conn = sqlite3.connect(path)
    curs = conn.cursor()
    curs.execute("SELECT Value FROM AutoManhourKeyValue WHERE Key='%s'" % key)
    try:
        value = curs.fetchone()[0]
        conn.close()
        return value
    except:
        conn.close()
        return None


def set_manhour_keyvalue(key, value, path="pyas.asdb"):
    conn = sqlite3.connect(path)
    curs = conn.cursor()
    curs.execute("INSERT INTO AutoManhourKeyValue VALUES ('%s', '%s')" % (key, value))
    conn.commit()
    conn.close()


def get_manhour_task(dateprefix):
    key = "task:%s" % dateprefix
    uuid = get_manhour_keyvalue(key)
    if uuid == None:
        uuid = add_ones_task("日常事务-%s" % dateprefix)
        set_manhour_keyvalue(key, uuid)
    return uuid


def auto_log_events(task_uuid, events):
    for event in events:
        key = "event:%s" % event['uuid']
        exist = get_manhour_keyvalue(key)
        if exist == None:
            start_at = event['start_at']
            start_unix = int(time.mktime(start_at.timetuple()))
            mins = event['duration_mins']
            title = event['title']
            if add_ones_manhour(start_unix, task_uuid, mins, title):
                set_manhour_keyvalue(key, "true")
                print 'add_ones_manhour: key: %s , task: %s, desc: %s , start at: %s, duration_mins: %2.f success' % \
                    (key, task_uuid, title.decode('utf-8', 'ignore'), start_at, mins)
            else:
                print 'add_ones_manhour: key: %s , task: %s, desc: %s , start at: %s, duration_mins: %2.f fail' % \
                      (key, task_uuid, title.decode('utf-8', 'ignore'), start_at, mins)

cookies = {}


def load_cookies():
    with open('cookies.json', 'r') as f:
        data = json.load(f)
        return data


headers = {
    'authority': 'ones.ai',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh',
    'content-type': 'application/json;charset=UTF-8',
    # Requests sorts cookies= alphabetically
    'elastic-apm-traceparent': '00-e9deb20d7da709f0d594cf70aef8bd06-3ce11b5c57340edb-01',
    'origin': 'https://ones.ai',
    'referer': 'https://ones.ai/project/',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36',
    'x-csrf-token': '7c14990d76ababc477c74898d063f6174d7929bdbfad5fb115d3c9e975f8fd26',
}


def randomstring(n=8):
    letters = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    return (''.join(random.choice(letters) for i in range(8)))


def add_ones_task(title="日常事务"):
    owner = '4n9rqe5k'
    uuid = owner + randomstring()
    json_data = {
        'tasks': [
            {
                'uuid': uuid,
                'owner': owner,
                'assign': owner,
                'summary': title,
                'parent_uuid': '',
                'field_values': [
                    {
                        'field_uuid': 'field004',
                        'type': 8,
                        'value': '4n9rqe5k',
                    },
                    {
                        'field_uuid': 'field012',
                        'type': 1,
                        'value': 'Lv5Tbmih',
                    },
                    {
                        'field_uuid': 'field029',
                        'type': 44,
                        'value': [],
                    },
                ],
                'project_uuid': 'KuZfE9scjSrGgi6r',
                'issue_type_uuid': 'UpZTPCYf',
                'add_manhours': [],
                'watchers': [
                    owner,
                ],
            },
        ],
    }
    response = requests.post('https://ones.ai/project/api/project/team/RDjYMhKq/tasks/add2', cookies=cookies,
                             headers=headers, json=json_data)
    print 'add_ones_task:', response
    return uuid


def add_ones_manhour(start_unix_time, taskUUID, mins, desc=''):
    hours = int(float("%.1f" % (mins/60.0)) * 100000)
    owner = '4n9rqe5k'
    json_data = {
        'query': '\n mutation AddManhour {\n addManhour (mode: $mode owner: $owner task: $task type: $type start_time: $start_time hours: $hours description: $description) {\n key\n }\n}\n',
        'variables': {
            'mode': 'detailed',
            'owner': owner,
            'task': taskUUID,
            'type': 'recorded',
            # 'start_time': 1654952400,
            'start_time': start_unix_time,
            # 'hours': 120000,
            'hours': hours,
            'description': desc,
        },
    }

    # print 'add_ones_manhour task: %s, desc: %s :' % \
    #       (taskUUID, desc.decode('utf-8', 'ignore'))
    response = requests.post('https://ones.ai/project/api/project/team/RDjYMhKq/items/graphql', cookies=cookies,
                             headers=headers, json=json_data)
    print "add_ones_manhour: " + desc + "response: \n", response.json()
    return response.status_code == 200


def main(days=0):
    global cookies
    cookies = load_cookies()
    init_kv_db()
    prefix = today_match_string(datetime.now() - timedelta(days=days))
    events = retrive_event_by_start_date_prefix(prefix)
    if len(events) <= 0:
        return
    task_uuid = get_manhour_task(prefix)
    auto_log_events(task_uuid, events)


if __name__ == '__main__':
    print 'start auto log manhour', datetime.now()
    # for i in range(15, 30):
    #     main(i)
    main(0)