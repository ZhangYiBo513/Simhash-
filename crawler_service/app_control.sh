#!/bin/bash

lock="$HOME/python_ctl.lock"
if [ -f $lock ];then
    echo $ck
    echo "$0 is running"
    exit 1
else
    touch $lock
fi
source /etc/profile

Usage()
 {
  echo "$0 action project"
  echo "action is start stop restart"
  rm -f $lock
  exit 1
 }

if [ $# -ne 3 ];then
    Usage
fi


action=$1
env=$2
port=$3
pycmd='python3'

project='bbtree-ecompython-crawlerSimhashService'
python_dir='/data/bbtree/python'
python_full="${python_dir}/${project}"
stop_app()
 {
   app_name=$project
   app_path=${python_full}
   tpid=`ps auxww|grep $pycmd|grep -v grep|grep ${project}|awk '{print $2}'`
   if [ "a$tpid" != "a" ];then
           kill -9 $tpid
           echo "$app_name is killed"
   fi  
 }

start_app()
 { 
  app_name=$project
  app_path=${python_full}
  tpid=`ps auxww|grep $pycmd|grep -v grep|grep ${app_path}|awk '{print $2}'`
  
  if [ "a$tpid" != "a" ];then
           echo "$app_name is running"
  else
      $pycmd ${python_full}/simhash_main.py $env $port >/dev/null 2>&1
  fi
 } 

case $action in
   stop)
          stop_app
          ;;
   start)
          start_app 
          ;;
   restart)
         stop_app 
         start_app
         ;;
        *)
          Usage
          ;; 
esac

rm -f $lock
exit 0
