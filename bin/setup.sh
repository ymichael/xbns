#!/usr/bin/env bash


install () {
    # Remove and uninstall the service (if exists).
    systemctl stop $1
    systemctl disable $1

    # Install the service.
    ln -s /home/michael/xbns/bin/$1 /etc/systemd/system/
    systemctl enable $1

    # Start the service and output the status
    systemctl start $1
    systemctl status $1
}

install xbns.service
install pong.service
install apps.service

ps aux | grep python
