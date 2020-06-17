pip install selenium

FILE=geckodriver
if [ -f "$FILE" ]; then
  export PATH=$PATH:$(pwd)
else
  wget --no-parent -r https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz
  mv github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz geckodriver-v0.26.0-linux64.tar.gz
  tar -xvzf geckodriver-v0.26.0-linux64.tar.gz
  rm -rf geckodriver-v0.26.0-linux64.tar.gz github.com

  export PATH=$PATH:$(pwd)
fi


if [ $# == 1 ]; then
  cd ..
  python run_service.py --path $1 --port 9002 &
  cd tests/
  python run.py

  PID=`ps aux | grep python | grep -v grep | awk '{print $2}'`

  for pid in $PID
  do
    kill -9 $pid
  done
else
  python run.py
fi
