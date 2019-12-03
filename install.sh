DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo "# added by conf_reg_pkg" >> $HOME/.bashrc
echo export PYTHONPATH='${PYTHONPATH}':${DIR} >> $HOME/.bashrc
echo export PATH='$PATH':${DIR}/conf_reg >> $HOME/.bashrc
