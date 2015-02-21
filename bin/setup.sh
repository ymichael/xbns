#!/usr/bin/env bash

# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

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
