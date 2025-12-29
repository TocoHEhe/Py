#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
STORAGE_DIR=/opt/render/project/.render/chrome
if [ ! -d "$STORAGE_DIR" ]; then
  mkdir -p $STORAGE_DIR
  cd $STORAGE_DIR
  wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x google-chrome-stable_current_amd64.deb .
fi
