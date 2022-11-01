#!/bin/sh

zcat jsonpog-integration/POG/MUO/2016preVFP_UL/muon_Z.json.gz |\
   jq ".corrections[].name"
