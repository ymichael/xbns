#!/usr/bin/env bash

install () {
    # Remove and uninstall the service (if exists).
    systemctl stop $1
    systemctl disable $1

    # Install the service.
    cp /home/michael/xbns/bin/$1 /lib/systemd/system/
    systemctl enable $1

    # Start the service and output the status
    systemctl start $1
    systemctl status $1
}


# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

if [ -z ${1+x} ]; then
    echo "Expect a service name (eg. xbns.service) as the first cli argument.";
    exit 1
else
    install $1
fi
