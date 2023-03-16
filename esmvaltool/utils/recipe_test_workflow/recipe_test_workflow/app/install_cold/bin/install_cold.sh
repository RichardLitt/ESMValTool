#!/bin/bash
# Send the output from 'set -x' to 'stdout' rather than 'stderr'.
BASH_XTRACEFD=1
set -eux


# Copy the site specific environment file to the 'bin' directory in the
# installed Cylc workflow (this directory is automatically added to the
# ${PATH} by Cylc).
SOURCE_PATH="${CYLC_WORKFLOW_RUN_DIR}/site/${SITE}-env"
TARGET_DIR="${CYLC_WORKFLOW_RUN_DIR}/bin"
ENV_FILE="rtw-env"

# Create the 'bin' directory in the installed workflow.
mkdir "${TARGET_DIR}"

# Copy the environment file to the 'bin' directory.
cp "${SOURCE_PATH}" "${TARGET_DIR}/${ENV_FILE}"
chmod u+x "${TARGET_DIR}/${ENV_FILE}"

# Remove the ESMValTool and ESMValCore directories, if they exist.
if [[ -d ${ESMVALTOOL_DIR} ]]; then
    rm -rf "${ESMVALTOOL_DIR}"
fi

if [[ -d ${ESMVALCORE_DIR} ]]; then
    rm -rf "${ESMVALCORE_DIR}"
fi

# Checkout the specified branch for ESMValCore and ESMValTool. Use the
# quiet ('-q') option to prevent the progress status from being reported
# (which is done via done via 'stderr').
git clone -q -b "${BRANCH}" "${ESMVALTOOL_URL}" "${ESMVALTOOL_DIR}"
cd "${ESMVALTOOL_DIR}"
git checkout 146c92b
git clone -q -b "${BRANCH}" "${ESMVALCORE_URL}" "${ESMVALCORE_DIR}"
cd "${ESMVALCORE_DIR}"
git checkout 4527173

# Manually and temporarily install imagehash (it will be included in the
# next ESMValTool community environment).
#rtw-env pip install imagehash -t "${CYLC_WORKFLOW_RUN_DIR}/lib/python"
