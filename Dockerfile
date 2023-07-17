FROM conda/miniconda3 as snap

USER root

# fix error "ttyname failed: Inappropriate ioctl for device"
RUN sed -i ~/.profile -e 's/mesg n || true/tty -s \&\& mesg n/g'

RUN apt-get update && apt-get install -y \
    software-properties-common
RUN apt-get install -y git python3-pip wget libpq-dev

# download SNAP installer
WORKDIR /tmp/
RUN wget https://download.esa.int/step/snap/9.0/installers/esa-snap_sentinel_unix_9_0_0.sh
COPY docker/esa-snap.varfile /tmp/esa-snap.varfile
RUN chmod +x esa-snap_sentinel_unix_9_0_0.sh

# install and update SNAP
RUN /tmp/esa-snap_sentinel_unix_9_0_0.sh -q /tmp/varfile esa-snap.varfile
RUN apt install -y fonts-dejavu fontconfig
COPY docker/update_snap.sh /tmp/update_snap.sh
RUN chmod +x update_snap.sh
RUN /tmp/update_snap.sh

FROM snap as ers_nrb

# install ERS_NRB
SHELL [ "/bin/bash", "--login", "-c" ]

COPY environment-tpz.yaml environment.yaml
RUN conda update conda
RUN conda env create --force --file environment.yaml

RUN echo "export PROJ_LIB=/usr/local/envs/nrb_env_tpz/share/proj" >> ~/.bashrc

RUN echo "conda init bash" >> ~/.bashrc
RUN source ~/.bashrc
RUN echo "conda activate nrb_env_tpz" >> ~/.bashrc

WORKDIR /app/
COPY . /app/
RUN source ~/.bashrc \
 && python -m pip install .


COPY docker/entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]