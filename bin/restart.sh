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
    rm /lib/systemd/system/$1

    # Install the service.
    cp /home/michael/xbns/bin/$1 /lib/systemd/system/
    systemctl enable $1

    # Start the service and output the status
    systemctl start $1
    systemctl status $1
}

install xbns.service
install apps.service

ps aux | grep python
