# encoding=utf-8
import os
import sys
import multiprocessing
import time
import shutil
from django.core.management import execute_from_command_line

log_dir = "/data/logs/bbtree-ecompython-crawlerSimhashService"  # 检查/创建log文件夹
current_dir = os.path.dirname(os.path.abspath(__file__))


def daemon_init(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):  # 修改为守护进程
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("first fork failed!!" + e.strerror)
        sys.exit(1)
    os.setsid()
    os.chdir("/")
    os.umask(0)
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("second fork failed!!" + e.strerror)
        sys.exit(1)
    sys.stdout.write("Daemon has been created! with pid: %d\n" % os.getpid())
    sys.stdout.flush()
    sys.stdin = open(stdin, 'r')
    sys.stdout = open(stdout, 'a+')
    sys.stderr = open(stderr, 'a+')


daemon_init()


def start_django(*para):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crawler_service.settings")
    execute_from_command_line(*para)


def change_env_setting(args):
    env = "dev"
    port = 62501
    print(current_dir)
    os.chdir(current_dir)
    for i in args[1:]:
        if i in ("prod", "beta", "dev", "local"):
            env = i
        elif i.isdigit():
            port = int(i)
        else:
            pass
    # 根据命令选择环境配置
    with open("./simhash_service/utils/{}".format(env), "r") as f_env:
        with open("./simhash_service/utils/setting", "w") as f_setting:
            f_setting.write(f_env.read())
    return env, port


def main():
    if os.path.isdir(log_dir):
        pass
    else:
        os.makedirs(log_dir)
    os.chdir(current_dir)
    env, port = change_env_setting(sys.argv)
    manage_path = os.path.join(current_dir, "manage.py")
    django_start = "{} runserver 0.0.0.0:{}".format(manage_path, port)
    os.chdir(current_dir)
    start_django(django_start.split(" "))


if __name__ == '__main__':
    main()
