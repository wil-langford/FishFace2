import os
import etc.fishface_config as ff_conf
import textwrap


def main():
    supervisor_config_string = textwrap.dedent("""
        [unix_http_server]
        file={var_run}/supervisor.sock    ; (the path to the socket file)
        chown=fishface:fishface                    ; socket file uid:gid owner

        [supervisord]
        logfile={var_log}/supervisord.log ; (main log file;default $CWD/supervisord.log)
        logfile_maxbytes=50MB                      ; (max main logfile bytes b4 rotation;default 50MB)
        logfile_backups=10                         ; (num of main logfile rotation backups;default 10)
        loglevel=info                              ; (log level;default info; others: debug,warn,trace)
        pidfile={var_run}/supervisord.pid ; (supervisord pidfile;default supervisord.pid)
        nodaemon=false                             ; (start in foreground if true;default false)
        minfds=1024                                ; (min. avail startup file descriptors;default 1024)
        minprocs=200                               ; (min. avail process descriptors;default 200)
        user=fishface                              ; (default is current user, required if root)
        directory={var}                   ; (default is not to cd during start)
        childlogdir={var_log}             ; ('AUTO' child log dir, default $TEMP)

        ; Required for RPC
        [rpcinterface:supervisor]
        supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

        [supervisorctl]
        serverurl=unix://{var_run}/supervisor.sock
        history_file=~/.sc_history                 ; use readline history if available

        [include]
        files = supervisor.d/enabled/*.conf"""
    ).format(
        var=ff_conf.VAR,
        var_log=ff_conf.VAR_LOG,
        var_run=ff_conf.VAR_RUN,
    )

    supervisor_conf_path = os.path.join(ff_conf.ETC, 'supervisor.conf')
    with open(supervisor_conf_path, 'wt') as supervisor_conf_file:
        print 'Writing', supervisor_conf_path
        supervisor_conf_file.write(supervisor_config_string)

    redis_config_string = textwrap.dedent("""
        [program:redis]
        command=/home/fishface/bin/redis-server {etc}/redis/redis.conf
        autostart=true
        autorestart=true
        user=fishface
        stdout_logfile={var_log}/redis.log
        stderr_logfile={var_log}/redis.err
        priority=50"""
    ).format(
        bin=ff_conf.BIN,
        etc=ff_conf.ETC,
        var_log=ff_conf.VAR_LOG
    )

    redis_conf_path = os.path.join(ff_conf.ETC, 'supervisor.d', 'available', 'redis_server.conf')
    with open(redis_conf_path, 'wt') as redis_conf_file:
        print 'Writing', redis_conf_path
        redis_conf_file.write(redis_config_string)


    for queue_name in ff_conf.CELERY_QUEUE_NAMES:

        config_file_string = textwrap.dedent("""
        [program:{worker}]
        command=%(ENV_HOME)s/.pyenv/shims/celery worker --app=lib.workers.{worker}_tasks -l {log_level} -Q {worker} -n '{worker}.%%h' --concurrency={concurrency} -O fair {threads}
        directory={root}
        user=fishface
        numprocs=1
        stdout_logfile={var_log}/workers/{worker}.log
        stderr_logfile={var_log}/workers/{worker}.err
        autostart=true
        autorestart=true
        stopwaitsecs=600
        killasgroup=true
        priority=100"""
        ).format(
            venv=ff_conf.VENV,
            log_level=ff_conf.LOG_LEVEL,
            root=ff_conf.ROOT,
            var_log=ff_conf.VAR_LOG,
            worker=queue_name,
            concurrency=4 if queue_name in ['results'] else 1,
            threads='' if queue_name in ['results'] else '-P solo',
        )

        conf_path = os.path.join(ff_conf.ETC, 'supervisor.d', 'available', queue_name + '.conf')
        with open(conf_path, 'wt') as conf_file:
            print 'Writing', conf_path
            conf_file.write(config_file_string)

if __name__ == '__main__':
    main()