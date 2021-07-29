#!/bin/bash
#
# Update onedriveDir with correct existing OneDrive directory path
#
onedriveDir="${HOME}/OOgle/data"
onedrive_conf="${HOME}/OOgle/docker/conf"
firstRun='-d'
docker pull driveone/onedrive
docker inspect onedrive > /dev/null && docker rm -f onedrive
# docker run -it --entrypoint /bin/bash --restart unless-stopped --name onedrive -v "${onedrive_conf}:/onedrive/conf" -v "${onedriveDir}:/onedrive/data" driveone/onedrive:latest
# docker run -it --entrypoint /usr/local/bin/onedrive --rm --name onedrive -v "${onedrive_conf}:/onedrive/conf" -v "${onedriveDir}:/onedrive/data" driveone/onedrive:latest --get-O365-drive-id 'Grp-Evolving Distributed Systems Lab - OOgle' --verbose
# docker run -it --entrypoint /usr/bin/bash --restart unless-stopped --name onedrive -v "${onedrive_conf}:/onedrive/conf" -v "${onedriveDir}:/onedrive/data" -v "${onedrive_config}:/root/.config/onedrive" driveone/onedrive:latest
# docker run -it --restart unless-stopped --name onedrive -v "${onedrive_conf}:/onedrive/conf" -v "${onedriveDir}:/onedrive/data" driveone/onedrive:latest

 
docker run -it --entrypoint /usr/local/bin/onedrive --restart unless-stopped --name onedrive -v "${onedrive_conf}:/onedrive/conf" -v "${onedriveDir}:/onedrive/data" -v "${onedrive_config}:/root/.config/onedrive" driveone/onedrive:latest --resync --synchronize --confdir /onedrive/conf --syncdir /onedrive/data --single-directory 'OOgle'


# onedrive --monitor --confdir /onedrive/conf --syncdir /onedrive/data --resync