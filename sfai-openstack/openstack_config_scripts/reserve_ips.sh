#!/usr/bin/env bash
for i in {1..22}; do nova-manage fixed reserve 172.27.34.$i; done
for i in {1..22}; do nova-manage floating delete 172.27.31.$i; done
