# encoding=utf-8
import datetime
import jieba
import jieba.analyse
import re
from simhash import Simhash
import itertools
import copy
import pymongo
import threading
from lxml import etree
import functools
import os
import logging
loggor = logging.getLogger("django")
# import time
# jieba.initialize()

# 读取配置文件
def mongo_setting():
    dir_name = os.path.dirname(os.path.abspath(__file__))
    cur = os.getcwd()
    os.chdir(dir_name)
    settings = {}
    with open("./utils/setting", "r", encoding="utf-8") as f:
        line = f.readline()
        while line:
            k, v = line.strip("\n").split("=")
            settings[k.strip()] = v.strip()
            line = f.readline()
    os.chdir(cur)
    return settings


def change_client(cl_setting):
    if "username" in cl_setting:
        #conn_addr1 = cl_setting["CONN_ADDR1"]
        #conn_addr2 = cl_setting["CONN_ADDR2"]
        #replicat_set = cl_setting["REPLICAT_SET"]
        host = cl_setting["host"]
        port = int(cl_setting["port"])
        username = cl_setting["username"]
        password = cl_setting["password"]
        #client = pymongo.MongoClient([conn_addr1, conn_addr2], replicaSet=replicat_set)
        client = pymongo.MongoClient(host, port)
        client.scrapy.authenticate(username, password)
    elif "host" in cl_setting:
        cl_setting["port"] = int(cl_setting["port"])
        client = pymongo.MongoClient(**cl_setting)
    else:
        client = None
    return client


SETTING = mongo_setting()
CL = change_client(SETTING)


class CheckSimilar(object):
    db = None
    if CL is None:
        db = pymongo.MongoClient(host="localhost", port=27017)
    else:
        db = CL
    """
    content: 传入需要去重的内容
    top_key_count: 最高频率的关键词数量
    tolerance:海明距离:3
    x_bit:64位分成五段后三段剩余的可能最大位数
    cl: mongoclient
    """
    x_bit = 39

    def __init__(self, content, top_key_count=40, tolerance=3):
        tree = etree.HTML(content)
        self.content = tree.xpath("string(.)")
        # 除了汉字英文其他都不能输出
        self.text = "".join(re.findall("[\u4E00-\u9FA5A-Za-z0-9_]+", self.content))
        self.word_weight = jieba.analyse.extract_tags(self.text, topK=top_key_count, withWeight=True)
        self.top_key_count = top_key_count
        self.tolerance = tolerance
        self.simhash = Simhash(self.word_weight)
        self.sim_value = self.simhash.value
        self._part_simhash = None
        self.res_list = []
        self._check_list = []

    def _is_similar(self, v):
        # 判断海明距离是否大于tolerance(3)
        if isinstance(v, int) and self._part_simhash is not None:
            x = (self._part_simhash ^ v) & ((1 << self.x_bit) - 1)
            ans = 0
            while x:
                ans += 1
                x &= x - 1
                if ans > self.tolerance:
                    return False
            return True
        else:
            error_info = "{} should be simhash or int".format(str(v))
            raise ValueError(error_info)

    # 检查simhash值列表simhash_table_list为已有数据simhash的10种排列
    def is_similar_list(self):
        self.res_list = []
        coll_list = list(["table_{}".format(i) for i in range(1, 11)])  # 格式化成64位字符串用于截取
        str_simhash = "{:0>64}".format(bin(self.sim_value)[2:])
        str_simhash_parts = []
        for i in range(4):  # 取出五个片段
            str_simhash_parts.append(str_simhash[13 * i:13 * (i + 1)])
        str_simhash_parts.append(str_simhash[52:])
        combine = list(itertools.combinations([0, 1, 2, 3, 4], 2))
        check_list = []
        for n, m in combine:  # 取五个片段取两个作为键，剩余作为值
            temp_str = copy.deepcopy(str_simhash_parts)
            key = int(temp_str.pop(n) + temp_str.pop(m - 1), base=2)
            value = int("".join(temp_str), base=2)
            check_list.append((key, value))
        self._check_list = check_list
        thread_list = []
        for I, J in enumerate(check_list):
            t = threading.Thread(target=self._query, args=(coll_list[I], J))  # 开线程同时查询mongo
            thread_list.append(t)
            t.start()
        for _thread in thread_list:
            _thread.join()
        if functools.reduce(lambda x, y: x or y, self.res_list):  # 检查结果列表
            return True
        else:
            insert_thread = []
            for i in range(10):
                t = threading.Thread(target=self._insert_table, args=(coll_list[i], self._check_list[i]))
                t.start()
                insert_thread.append(t)
            for _thread in insert_thread:
                _thread.join()
            return False

    def _query(self, table_n, obj):  # 查询mongo并检查海明距离
        res = self.db.scrapy[table_n].find_one({"first": obj[0]})
        if res:
            self._part_simhash = obj[1]
            for v in res["rest"]:
                if self._is_similar(v):
                    self.res_list.append(True)
                    break
            else:
                self.res_list.append(False)
        else:
            self.res_list.append(False)

    def _insert_table(self, table_n, k_v):  # 对新simhash进行插入
        res = self.db.scrapy[table_n].find_one({"first": k_v[0]})
        if res:
            rest = res["rest"]
            rest.append(k_v[1])
            try:
                self.db.scrapy[table_n].update({"first": k_v[0]}, {"$set": {"rest": rest}})

            except Exception as e:
                loggor.error("{},failed to insert {} to {} ".format(e, k_v, table_n))
        else:
            try:
                self.db.scrapy[table_n].insert_one({"first": k_v[0], "rest": [k_v[1]]})
            except Exception as e:
                loggor.error("{},failed to insert {} to {} ".format(e, k_v, table_n))

    def close(self):
        self.db.close()
