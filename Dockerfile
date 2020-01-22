### initial setup from https://github.com/BIC-MNI/build_packages/blob/master/build_ubuntu_18.04_x64/Dockerfile
FROM ubuntu:bionic

# install basic system packages
RUN apt-get -y update && \
    apt-get -y dist-upgrade && \
    apt-get install -y --no-install-recommends \
         sudo \
         build-essential g++ gfortran bc \
         bison flex \
         libx11-dev x11proto-core-dev \
         libxi6 libxi-dev \
         libxmu6 libxmu-dev libxmu-headers \
         libgl1-mesa-dev libglu1-mesa-dev \
         libjpeg-dev \
         libssl-dev ccache libapt-inst2.0 git lsb-release \
         curl ca-certificates && \
    apt-get autoclean && \
    rm -rf /var/lib/apt/lists/*

# add user to build all tools
RUN useradd -ms /bin/bash conf_reg && \
    echo "conf_reg ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/conf_reg && \
    chmod 0440 /etc/sudoers.d/conf_reg

ENV PATH=/usr/lib/ccache:$PATH

# add new cmake
RUN mkdir src && \
    cd src && \
    curl -L --output cmake-3.14.5.tar.gz https://github.com/Kitware/CMake/releases/download/v3.14.5/cmake-3.14.5.tar.gz  && \
    tar zxf cmake-3.14.5.tar.gz && \
    cd cmake-3.14.5 && \
    ./configure --prefix=/usr --no-qt-gui && \
    make && \
    make install && \
    cd ../../ && \
    rm -rf src

WORKDIR /home/conf_reg
ENV HOME="/home/conf_reg"

# install FSL
RUN sudo apt-get update && \
  sudo apt-get install -y --no-install-recommends gnupg gnupg2 gnupg1
RUN git clone https://github.com/poldracklab/mriqc.git && \
  mv mriqc/docker/files/neurodebian.gpg $HOME && \
  rm -rf mriqc

RUN curl -sSL "http://neuro.debian.net/lists/$( lsb_release -c | cut -f2 ).us-ca.full" >> /etc/apt/sources.list.d/neurodebian.sources.list && \
  sudo apt-key add /home/conf_reg/neurodebian.gpg && \
  (apt-key adv --refresh-keys --keyserver hkp://ha.pool.sks-keyservers.net 0xA5D32F012649A5A9 || true)

RUN sudo ln -fs /usr/share/zoneinfo/America/Montreal /etc/localtime && \
  sudo apt-get install -y --no-install-recommends tzdata && \
  sudo dpkg-reconfigure -f noninteractive tzdata && \
  sudo apt-get update && \
  sudo apt-get install -y --no-install-recommends fsl-core && \
  sudo apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Configure FSL environment
ENV export FSLDIR="/usr/share/fsl/5.0/" \
  export FSL_DIR="${FSLDIR}" \
  export FSLOUTPUTTYPE=NIFTI_GZ \
  . ${FSLDIR}/etc/fslconf/fsl.sh \
  export PATH="/usr/share/fsl/5.0/bin:$PATH" \
  export LD_LIBRARY_PATH=/usr/lib/fsl/5.0:$LD_LIBRARY_PATH

### install ANTs
RUN apt-get update -qq \
    && sudo apt-get install -y -q --no-install-recommends \
           gcc \
           g++ \
           graphviz \
           tree \
           git \
           vim \
           emacs-nox \
           nano \
           less \
           ncdu \
           tig \
           git-annex-remote-rclone \
           netbase \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Installing ANTs 2.3.1 based on neurodocker
ENV ANTSPATH="$HOME/ants-v2.3.1/bin" \
    PATH="$HOME/ants-v2.3.1/bin:$PATH" \
    LD_LIBRARY_PATH="$HOME/ants-v2.3.1/lib:$LD_LIBRARY_PATH"
RUN apt-get update -qq \
    && apt-get install -y -q --no-install-recommends \
           cmake \
           g++ \
           gcc \
           git \
           make \
           zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /tmp/ants/build \
    && git clone https://github.com/ANTsX/ANTs.git /tmp/ants/source \
    && cd /tmp/ants/source \
    && git fetch --tags \
    && git checkout v2.3.1 \
    && cd /tmp/ants/build \
    && cmake -DBUILD_SHARED_LIBS=ON /tmp/ants/source \
    && make -j1 \
    && mkdir -p $HOME/ants-v2.3.1 \
    && mv bin lib $HOME/ants-v2.3.1/ \
    && mv /tmp/ants/source/Scripts/* $HOME/ants-v2.3.1/bin \
    && rm -rf /tmp/ants



#Install python environment

ENV CONDA_DIR="$HOME/miniconda-latest" \
    PATH="$HOME/miniconda-latest/bin:$PATH" \
    ND_ENTRYPOINT="$HOME/startup.sh"

RUN export PATH="$HOME/miniconda-latest/bin:$PATH" \
    && echo "Downloading Miniconda installer ..." \
    && conda_installer="/tmp/miniconda.sh" \
    && curl -fsSL --retry 5 -o "$conda_installer" https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash "$conda_installer" -b -p $HOME/miniconda-latest \
    && rm -f "$conda_installer" \
    && conda update -yq -nbase conda

RUN mkdir -p temp && \
    curl -L --retry 5 -o temp/RABIES.tar.gz https://github.com/CoBrALab/RABIES/archive/0.1.2.tar.gz && \
    cd temp && \
    tar zxf RABIES.tar.gz && \
    cd .. && \
    conda env create -f temp/RABIES-0.1.2/rabies_environment.yml && \
    rm -r temp

# install confound regression package
RUN git clone https://github.com/Gab-D-G/conf_reg_pkg.git $HOME/conf_reg_pkg && \
  echo export PYTHONPATH='${PYTHONPATH}':$HOME/conf_reg_pkg >> $HOME/.bashrc && \
  echo export PATH='$PATH':$HOME/conf_reg_pkg/conf_reg >> $HOME/.bashrc

RUN echo "#! /home/conf_reg/miniconda-latest/envs/rabies/bin/python" > temp && \
  echo "import os" >> temp && \
  echo "import sys" >> temp && \
  echo "os.environ['PATH'] = '${HOME}/conf_reg_pkg/conf_reg:${HOME}/miniconda-latest/envs/rabies/bin:${PATH}'" >> temp && \
  echo "os.environ['PYTHONPATH'] = '${HOME}/conf_reg_pkg:${PYTHONPATH}'" >> temp && \
  echo "sys.path.insert(0,'${HOME}/conf_reg_pkg')" >> temp && \
  cat temp | cat - $HOME/conf_reg_pkg/conf_reg/confound_regression.py > tmp && mv tmp $HOME/conf_reg_pkg/conf_reg/confound_regression.py && \
  chmod +x $HOME/conf_reg_pkg/conf_reg/confound_regression.py

WORKDIR /tmp/
RUN /bin/bash -c "source activate rabies"

ENTRYPOINT ["/home/conf_reg/conf_reg_pkg/conf_reg/confound_regression.py"]
