#!/bin/sh
f="weeks/$1"
[ -s "$f" ] && exit 0
curl -s --retry 3 "https://raw.githubusercontent.com/GeoDS/COVID19USFlows-WeeklyFlows/master/weekly_flows/county2county/$1" | grep -E "^(29007|29019|29151)," > "$f.tmp" && mv "$f.tmp" "$f"
