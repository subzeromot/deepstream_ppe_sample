#!/bin/bash

## CHECK ROOT USER
if [ $USER = "root" ]; then
  echo "ROOT USER"
else
  echo "NONROOT USER, Please login to root user by run 'sudo su' then re-run script"
  exit -1
fi
## AUTO SYNC TIME
apt install -y ntp curl
xx=$(curl -v --insecure --silent https://google.com/ 2>&1  | grep Date | sed -e 's/< Date: //'); date -s "${xx}"
timedatectl status
timedatectl set-ntp true
timedatectl status

## INSTALL NODEJS AND PM2
curl -sL https://deb.nodesource.com/setup_16.x | sudo -E bash -
apt update && apt install nodejs -y
npm config set strict-ssl=false
npm i -g pm2

## INSTALL PYDEEPSTREAM
git clone --recursive https://github.com/NVIDIA-AI-IOT/deepstream_python_apps
apt install python3-dev python3-pip cmake g++ build-essential libssl-dev libxinerama1 libxinerama-dev libxcursor-dev libglib2.0-dev libglib2.0-dev-bin python-gi-dev libtool m4 autoconf automake -y
cd deepstream_python_apps/3rdparty/gst-python
./autogen.sh
make install -j2
cd ../../bindings
mkdir build && cd build
cmake ..  -DPYTHON_MAJOR_VERSION=3 -DPYTHON_MINOR_VERSION=6
make -j2
cp pyds.so ../../..
cd ../../..
rm -rf deepstream_python_apps

## INSTALL APP DEPENDENCES
python3 -m pip install --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --trusted-host pypi.org pip --upgrade
python3 -m pip install --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --trusted-host pypi.org -r requirements.txt

