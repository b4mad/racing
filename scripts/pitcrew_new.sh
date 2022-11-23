set -o allexport -o pipefail -ex

# Pre-condition:
# - Create the config file at location ${PAYLOAD_PATH}
# - Clone the github.com/b4mad/racing repo at location ${WORKING_DIR}
# - Working branch should be clean, checked out of upstream default branch.
# - Set Environment variables: ORG_NAME (=b4mad), SOURCE_REPO (=racing), ISSUE_NUMBER
#
# If you want to run this script locally, you can set the following environment variables:
# - create a data.yaml file in the root of the repo
# - ISSUE_NUMBER=123 ./scripts/new_pitcrew.sh

# get config from environment or default to data.yaml
CONFIG=${PAYLOAD_PATH:-data.yaml}
if [ -z "$WORKING_DIR" ]; then
    REPO=$(pwd)
else
    REPO=${WORKING_DIR}/racing
fi
ORG_NAME=${ORG_NAME:-b4mad}
SOURCE_REPO=${SOURCE_REPO:-racing}
if [ -z "$ISSUE_NUMBER" ]; then
    echo "ISSUE_NUMBER is not set"
    exit 1
fi

# Unpack Config file, we will need these environment variables for the remainder of the steps
DRIVER_NAME=$(yq e .driver-name ${CONFIG})

# lower case the driver name
DRIVER_NAME_DASHED=$(echo ${DRIVER_NAME} | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

# Create deployment for driver

cd ${REPO}
PITCREW_PATH="${REPO}/manifests/pitcrew/";
jsonnet --ext-str DRIVER_NAME \
  --ext-str DRIVER_NAME_DASHED \
  scripts/jsonnet/pitcrew.jsonnet | yq -P > ${PITCREW_PATH}/${DRIVER_NAME_DASHED}.yaml
cd ${PITCREW_PATH}
kustomize edit add resource ${DRIVER_NAME_DASHED}.yaml

# Commit changes
cd ${REPO}
git add manifests/pitcrew
git commit -m "Onboarding pitcrew for ${DRIVER_NAME}."

set -o allexport
