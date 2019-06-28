# encoding=utf-8
# from django.shortcuts import render
# Create your views here.
from django.http import JsonResponse
# from django.http import request
from .sim_hash import CheckSimilar
import jieba
# import json
from lxml import etree
# import time
import threading
import logging
jieba.initialize()
sim_lock = threading.RLock()
logger = logging.getLogger("django")


def check_sim(request):
    if request.method == "POST":
        content = request.POST.get("content", None)
        if not content:
            return JsonResponse({"result": "no content"})
        tree = etree.HTML(content)
        content = tree.xpath("string(.)")
        sim = CheckSimilar(content)
        sim_lock.acquire()
        res = sim.is_similar_list()
        sim_lock.release()
        if res:
            logs = "content:{} res:{} sim_value:{}".format(content[:10], "similar", sim.sim_value)
            logger.info(logs)
            return JsonResponse({"result": True, "sim_value": sim.sim_value})
        else:
            logs = "content:{} res:{} sim_value:{}".format(content[:10], "Unsimilar", sim.sim_value)
            logger.info(logs)
            return JsonResponse({"result": False, "sim_value": sim.sim_value})
    else:
        return JsonResponse({"result": "wrong method"})


def alive(request):
    return JsonResponse({"status": "alive"})
