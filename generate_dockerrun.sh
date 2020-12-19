#!/bin/bash

# current script directory path
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# $1 is the path to the template file from this directory
# $2 will be the environement name passed to the script : it can only be dev or prod
# if empty, we ask for user input for convenience
if [ "$2" == "" ]; then
  echo -n "Enter your the image tag (either 'latest' or 'master') and press [ENTER]:"
  read ENV
else
  ENV=$2
fi

# check if environment name is valid
if [ "$ENV" == "latest" ] || [ "$ENV" == "master" ] ; then

  # move to shell script directory
  cd $DIR

  # generate Dockerfile from template by replacing the ENV property by the input
  echo "Generating Dockerrun.aws.json..."
  sed -e "s/\${ENV}/$ENV/g" $1 > Dockerrun.aws.json

  # do other things here if necessary

else
  echo "$ENV is not a valid environment name, accepted values : latest & master"
  exit 0
fi