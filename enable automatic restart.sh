#!/bin/bash

echo "enable monitoring"
sudo systemctl enable solar2heater.service
sudo systemctl start solar2heater.service
sudo monit monitor solar2heater

sudo systemctl status solar2heater.service
sudo monit summary
