FROM bitnami/pytorch:1.13.1

# This builds a slim image with torch and transformers
# for use with huggingface models. It is for CPU useage:
# See https://huggingface.co/docs/transformers/installation
#
# It also installs Starlett/Uvicorn so you can put an http wrapper around the service

# Copy the py/requirements.pip file and install the packages 
COPY py/requirements.pip /tmp/
RUN pip3 install -r /tmp/requirements.pip

# Set the transformers cache to a writeable directory: otherwise you get this error:
#  "There was a problem when trying to write in your cache folder (/.cache/huggingface/hub)."
ENV TRANSFORMERS_CACHE=/tmp/xformer_cache

# Download the models specified in question_answering.py using download_models.py 
COPY py/question_answering.py /tmp/
COPY py/download_models.py /tmp/
COPY py/opensearch_client.py /tmp/
RUN python3 /tmp/download_models.py 

