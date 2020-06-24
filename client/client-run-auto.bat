@echo off
title PyChat Client
start "PyChat Client" python client_quiet.py
ping -n 2 127.0.0.1>nul
start "PyChat Client - Receiver" python receiver_quiet.py
exit