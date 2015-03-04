# Setting up the beaglebone
_(bone is aliased to 192.168.7.2)_

0. ssh into device

```
ssh root@bone
```

1. create user `michael`

https://www.digitalocean.com/community/tutorials/how-to-add-and-delete-users-on-an-ubuntu-14-04-vps

```
sudo adduser michael
```

2. grant sudo permissions.


```
sudo visudo

# If you prefer vi
sudo EDITOR=vi visudo

# Add new line:
# michael ALL=(ALL:ALL) ALL
```

3. copy ssh public key onto device (to allow passwordless rsync)

https://www.digitalocean.com/community/tutorials/how-to-set-up-ssh-keys--2

```
# my public key is called bone.pub
cat ~/.ssh/bone.pub | ssh michael@192.168.7.2 "mkdir -p ~/.ssh && cat >>  ~/.ssh/authorized_keys"
```

4. copy code over.
```
make rsync
```

5. assign the device a unique ID (mark on the device exterior as well).

```
ssh michael@bone "echo 5 > ~/xbns/addr.txt"
```

6. add services (`make setup`)
```
# ssh-ed into device.
# Copy file
sudo cp ~/xbns/bin/xbns.service /lib/systemd/system/

# Enable service
sudo systemctl enable xbns.service

# Start service
sudo systemctl start xbns.service

# See status (optional)
sudo systemctl status xbns.service
```

- Add xbns.service, pong.service, apps.service.
- NOTE: xbns.service requires the xbee to be plugged in when it is run.
- use `ps aux | grep python` to check after starting all the services.

7. remove services (for debugging and uninstalling.)

```
sudo systemctl disable xbns.service

sudo rm /lib/systemd/system/xbns.service

sudo systemctl status xbns.service
```
