import sys
from datetime import datetime

import pymysql
import requests

# url = "http://zjj.sz.gov.cn/ris/bol/szfdc/projectdetail.aspx?id=49513"
# result = urllib.parse.urlsplit(url)
# query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
# ip = urllib.parse.urlsplit(url).netloc
#
# path = urllib.parse.urlsplit(url).path
# new_url = urllib.parse.urlparse(url)
#
#
# print('第一、urllib.parse.urlsplit(url)=', result)
# print('第二、dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))=', query)
# print('ip或者域名=', ip)
# print('ip或者域名=', new_url.netloc)
# print('path路径=', path)
# print('id=', query['id'])
class sz_fangdichan_chat_d():
    # 初始化函数
    def __init__(self):
        self.baseUrl = 'http://www.stats.gov.cn/sj/tjbz/tjyqhdmhcxhfdm/2023/index.html'
        self.base = 'http://www.stats.gov.cn/sj/tjbz/tjyqhdmhcxhfdm/2023/'

        import os, sys
        mysql_host = os.environ.get("MYSQL_HOST", '192.168.8.103')
        mysql_db = os.environ.get("MYSQL_DATABASE", 'quant_atlas')
        mysql_user = os.environ.get("MYSQL_USER", 'admin')
        mysql_password = os.environ.get("MYSQL_PASSWORD") or ""
        mysql_port = int(os.environ.get("MYSQL_PORT", "3307"))
        if not os.environ.get("MYSQL_PASSWORD"):
            print("WARNING: Using default DB password. Set MYSQL_PASSWORD env var.", file=sys.stderr)

        self.conn = pymysql.connect(host=mysql_host, port=mysql_port, user=mysql_user, password=mysql_password,
                                    db=mysql_db,
                                    charset='utf8')
        # self.conn = MySQLdb.connect(host="127.0.0.1", port=3306, user="root", passwd="123456", db="test", charset='utf8')
        self.cur = self.conn.cursor()

    def __del__(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
    # 插入数据库
    def insert_to_db(self, json):
        # return 0
        param = []
        lastid = 0
        try:
            sql = 'INSERT INTO sz_fangdichan_chat_d(date,esfDealArea,esfTotalTs,ysfDealArea,ysfTotalTs) values(%s,%s,%s,%s,%s)'
            for date, esfDealArea, esfTotalTs, ysfDealArea, ysfTotalTs in zip(json['data']['date'],
                                                                              json['data']['esfDealArea'],
                                                                              json['data']['esfTotalTs'],
                                                                              json['data']['ysfDealArea'],
                                                                              json['data']['ysfTotalTs']):
                dto = datetime.strptime(date, '%Y-%m-%d').date()
                print(type(dto),type(esfDealArea),type(esfTotalTs),type(ysfDealArea),type(ysfTotalTs))
                print(dto,esfDealArea,esfTotalTs,ysfDealArea,ysfTotalTs)

                param = (
                dto, esfDealArea, esfTotalTs,  ysfDealArea, ysfTotalTs)
                self.cur.execute(sql, param)
            self.conn.commit()
        except Exception as e:
            print(e)
            self.conn.rollback()
        return lastid

    def parseData(self,startDate,endDate):
       #url = 'https://zjj.sz.gov.cn:8004/api/marketInfoShow/getFjzsInfoData'
        url = 'https://fdc.zjj.sz.gov.cn/api/marketInfoShow/getFjzsInfoData'
        payload = {
            'dateType': "",
            'endDate': "2024-09-18",
            'startDate': "2024-09-08"}
        payload['startDate'] = startDate
        payload['endDate'] = endDate
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
                   'Accept': '*/*'
                   }
        response = requests.post(url, json=payload, headers=headers)
        json = response.json()
        #print(json)
        return json
if __name__ == '__main__':
    startDate = sys.argv[1]
    endDate = sys.argv[2]
    chinese_city = sz_fangdichan_chat_d()
    json = chinese_city.parseData(startDate,endDate)
    chinese_city.insert_to_db(json)
