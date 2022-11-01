#!/bin/sh

zcat jsonpog-integration/POG/EGM/2016postVFP_UL/electron.json.gz  | \
     jq ".corrections[].data.content[].value.content[].value.content[].key"
