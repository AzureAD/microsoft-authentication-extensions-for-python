#!/usr/bin/bash
IMAGE_NAME=msal-extensions:latest

docker build -t $IMAGE_NAME - < Dockerfile

echo "==== Integration Test for Persistence on Linux (libsecret) ===="
echo "After seeing the bash prompt, run the following to test encryption on Linux:"
echo "    pip install -e ."
echo "    pytest -s tests/chosen_test_file.py"
echo "Note that you probably need to set up ENV VAR for the test cases to run"
docker run --rm -it \
    --privileged \
    --env-file .env \
    -w /home -v $PWD:/home \
    $IMAGE_NAME \
    $1

