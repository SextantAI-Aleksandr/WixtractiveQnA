#!/bin/bash 

# This script uses docker-compose to spin up the app

# Verify you have key environment variables
echo "CHECK KEY ENVIRONMENT VARIABLES BEFORE CONTINUING:?"
echo "OPENSEARCH_DATADIR=$OPENSEARCH_DATADIR"
echo "NGINX_PORT=$NGINX_PORT"
echo ""
read -r -p "Press any key to continue... " response



# set directory permissions
# if you try to spin up opensearch before setting permissions for a NEW container (with no data),
# you may need to delete the old data directory first
echo "modifying $OPENSEARCH_DATADIR"
mkdir -p $OPENSEARCH_DATADIR
sudo chmod -R g+wrx $OPENSEARCH_DATADIR
sudo chgrp -R 0 $OPENSEARCH_DATADIR


# spin up the containers
envsubst < docker-template.yml > docker-secrets.yml
sudo docker-compose -f docker-secrets.yml up 
