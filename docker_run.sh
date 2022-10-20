#!/usr/bin/bash
IMAGE_NAME=msal-extensions:latest

docker build -t $IMAGE_NAME - < Dockerfile

echo "==== Integration Test for Persistence on Linux (libsecret) ===="
echo "After seeing the bash prompt, run the following to test encryption on Linux:"
echo "    pip install -e ."
echo "    pytest --capture=no -s tests/chosen_test_file.py"
echo "Note: It will test portalocker-based lock when portalocker is installed, or test file-based lock otherwise."
docker run --rm -it \
    --privileged \
    -w /home -v $PWD:/home \
    $IMAGE_NAME \
    $1

