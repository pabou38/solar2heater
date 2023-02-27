#!/bin/bash

echo "disable monitoring"
sudo systemctl disable solar2heater.service
sudo systemctl stop solar2heater.service
sudo monit unmonitor solar2heater
