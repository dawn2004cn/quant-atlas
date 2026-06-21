@echo off
if "%MYSQL_PASSWORD%"=="" set "MYSQL_PASSWORD="
if "%MYSQL_HOST%"=="" set "MYSQL_HOST=192.168.8.103"
if "%MYSQL_PORT%"=="" set "MYSQL_PORT=3307"
if "%MYSQL_USER%"=="" set "MYSQL_USER=root"
if "%MYSQL_DATABASE%"=="" set "MYSQL_DATABASE=quant_atlas"
echo 查询研报最新日期...
python -c "import os,pymysql; h=os.environ.get('MYSQL_HOST','192.168.8.103'); u=os.environ.get('MYSQL_USER','root'); p=os.environ.get('MYSQL_PASSWORD',""); d=os.environ.get('MYSQL_DATABASE','quant_atlas'); conn=pymysql.connect(host=h,user=u,password=p,database=d); cursor=conn.cursor(); cursor.execute('SELECT MAX(publish_date) FROM yanbao_items'); print('最新日期:', cursor.fetchone()[0]); cursor.execute('SELECT COUNT(*) FROM yanbao_items'); print('总数:', cursor.fetchone()[0]); conn.close()"
pause