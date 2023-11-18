#!/bin/sh
while true
do
    flask db upgrade
    if [ $? -eq 0 ]
    then
        break
    fi
    echo "Upgrade command failed, retrying in 5 secs..."
    sleep 5
done

python main.py