#!/bin/bash

echo "start service"
sudo systemctl enable solar2heater.service
sudo systemctl start solar2heater.service

sudo systemctl status solar2heater.service

echo "enable monitoring"
sudo monit monitor solar2heater
sudo monit summary
