#!/bin/bash
# Python 3 launcher with stdout and stderr to file
cd "$(dirname "${BASH_SOURCE[0]}")" || exit
name=$(basename "${BASH_SOURCE[0]}")
name=${name%.*}
command="python3 -u pool_scraper.py"
function doStart() {
  pid=$(pidof "$name")
  if [ ! "$pid" ]; then
    rm "$name.out" "$name.err"
    bash -c "exec -a $name $command &" 1>>"$name.out" 2>>"$name.err"
  fi
  sleep 1
  pid=$(pidof "$name")
  if [ "$pid" ]; then
    echo "$pid started"
  else
    cat "$name.out" "$name.err"
    exit 10
  fi
}

function doStop() {
  pid=$(pidof "$name")
  # shellcheck disable=SC2086
  if [ "$pid" ]; then
    kill $pid
    while kill -0 $pid 2>/dev/null; do
      sleep 1
    done
    echo "$pid stopped"
  fi
}

trap 'onCtrlC' INT

function onCtrlC() {
  doStop
}

if [ "$1" == "stop" ]; then
  doStop
  exit
elif [ "$1" == "start" ]; then
  doStart
  exit
elif [ "$1" == "restart" ]; then
  doStop
  doStart
  exit
else
  doStart
  tail --pid="$pid" -qf "$name.out" "$name.err"
fi