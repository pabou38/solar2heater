#!/bin/bash

echo "==>: disable monit monitoring"
sudo monit unmonitor solar2heater


echo "==>: disable and stop service (systemd)"
sudo systemctl disable solar2heater.service
sudo systemctl stop solar2heater.service
