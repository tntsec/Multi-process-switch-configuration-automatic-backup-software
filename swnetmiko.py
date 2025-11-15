from multiprocessing import Pool
import os,json,time,requests,redis,multiprocessing,codecs
from netmiko import ConnectHandler

def get_config():
    config = json.loads(open("swnetmiko.json", encoding='utf-8').read()) #读取配置文件
    return config

def post_weixin(stats): #发送微信
    url = swnetmiko_config['weixin']['url']
    body = {
        "msgtype": "news",
        "news": {
            "articles": [
                {
                    "title": swnetmiko_config['weixin']['title'],
                    "description": tianqi()+yiyan()+stats,
                    "url": swnetmiko_config['weixin']['url2'],
                    "picurl": swnetmiko_config['weixin']['picurl']
                }
            ]
        }}
    response = requests.post(url, json=body)
    print(response.text)
    print(response.status_code)
def yiyan():
    try:
        url = 'https://v1.hitokoto.cn/?c=d&c=k'
        response = requests.get(url)
        res = json.loads(response.text)
        text1 = res['hitokoto']
        if res['from'] == None:
            text2 = ""
        else:
            text2 = res['from']
        if res['from_who'] == None:
            text3 = ""
        else:
            text3 = res['from_who']
        return text1 + " " + text2 + " " + text3 + "\n\n"
    except:
        return "一言API故障\n\n"


def tianqi():
    try:
        response2 = requests.get(swnetmiko_config['weatherapi'])
        data1 = json.loads(response2.text)
        data2 = json.dumps(data1['now'])
        data2 = json.loads(data2)
        data3 = "环境温度" + data2['temp'] + " 体感温度" + data2['feelsLike'] + " 天气状况 " + data2[
                'text'] + "\n风向 " + data2['windDir'] + " 风力等级" + data2['windScale'] + " 风速" + data2[
                        'windSpeed'] + " 湿度" + data2['humidity'] + " 能见度" + data2['vis'] + "公里\n\n"
        return data3
    except:
        return "天气API故障\n\n"


dirpath = os.path.abspath('.')  # 配置运行目录为当前目录
nowtime = time.strftime("%Y%m%d", time.localtime())  # 获取当前日期
try:
    os.mkdir(dirpath + "/" + nowtime)
    print("创建当日目录")
except:
    print("当日目录已存在")
nowdir = (dirpath + "/" + nowtime)
print(nowdir)
swnetmiko_config = get_config()  # 读取配置文件
readredis = redis.Redis(connection_pool=redis.ConnectionPool(host=swnetmiko_config['redis']['host'],
                                                                 port=swnetmiko_config['redis']['port'],
                                                                 password=swnetmiko_config['redis']['password'],
                                                                 decode_responses=swnetmiko_config['redis']['decode']))

def sw_save(swconfig):  #保存交换机配置
    try:
        net_connect = ConnectHandler(**swconfig)
        output = net_connect.send_command("dis cu")
        print(swconfig['ip']+" OK")
        readredis.set(swconfig['ip'], "success")
        saveconfig = codecs.open(nowdir +'/'+ swconfig['ip'] +".conf", 'w+', encoding='utf-8')
        saveconfig.write(output)
        saveconfig.close()
    except:
        print(swconfig['ip'] + " NO")
        readredis.set(swconfig['ip'], "fail")

if __name__ == '__main__':
    total = 0
    fail = 0
    weixindata = ""
    readredis.flushall()
    print("初始化redis数据库")
    #multiprocessing.freeze_support() #防止windows无限创建进程
    multi_process = int(swnetmiko_config["multi-process"])
    with Pool(multi_process) as p:
        p.map(sw_save, swnetmiko_config["data"])
    for key in swnetmiko_config["data"]:
        if readredis.get(key["ip"]) == "fail":
            weixindata = weixindata + (key["ip"]+" 网络或账号密码错误\n")
            fail = fail + 1
        total = total + 1
    weixinpost = "总计巡检:"+str(total)+"台"+"，故障交换机："+str(fail)+"台\n"+weixindata
    post_weixin(weixinpost)
    flog = codecs.open(nowdir + "/" + nowtime + ".log", 'w', encoding='utf-8')
    flog.write(weixinpost)
    flog.close()
    print("程序执行完成")
