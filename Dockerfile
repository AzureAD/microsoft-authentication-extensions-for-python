# TODO: Can this Dockerfile use multi-stage build?
# Final size 690MB. (It would be 1.16 GB if started with python:3 as base)
FROM python:3-slim

# Install Generic PyGObject (sans GTK)
#The following somehow won't work:
#RUN apt-get update && apt-get install -y python3-gi python3-gi-cairo
RUN apt-get update && apt-get install -y \
  libcairo2-dev \
  libgirepository1.0-dev \
  python3-dev
RUN pip install "pygobject>=3,<4"

# Install MSAL Extensions dependencies
# Don't know how to get container talk to dbus on host,
# so we choose to create a self-contained image by installing gnome-keyring
RUN apt-get install -y \
  gir1.2-secret-1 \
  gnome-keyring

# Not strictly necessary, but we include a pytest (which is only 3MB) to facilitate testing.
RUN pip install "pytest>=6,<7"

# Install MSAL Extensions. Upgrade the pinned version number to trigger a new image build.
RUN pip install "msal-extensions==0.3"

# This setup is inspired from https://github.com/jaraco/keyring#using-keyring-on-headless-linux-systems-in-a-docker-container
ENTRYPOINT ["dbus-run-session", "--"]
# Note: gnome-keyring-daemon needs previleged mode, therefore can not be run by a RUN command.
CMD ["sh", "-c", "echo default_secret | gnome-keyring-daemon --unlock; bash"]
