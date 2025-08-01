#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2008-2024 Luis Falcón <falcon@gnuhealth.org>
# SPDX-FileCopyrightText: 2011-2024 GNU Solidario <health@gnusolidario.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

#########################################################################
#   Hospital Management Information System (HMIS) component of the      #
#                       GNU Health project                              #
#                   https://www.gnuhealth.org                           #
#########################################################################
#                      start_gnuhealth.sh                               #
#              The GNU Health HMIS startup script                       #
#########################################################################

message()
{
    local UTC="$(date -u +'%Y-%m-%d %H:%M:%S')"
    
    case $1 in
      ERROR ) echo -e "\e[00;31m${UTC} [ERROR] $2\e[00m";;
      WARNING ) echo -e "\e[0;33m${UTC} [WARNING] $2\e[m" ;;
      INFO ) echo -e "\e[0;36m${UTC} [INFO] $2\e[m" ;;
    esac
}

bailout() 
{
    message "ERROR" "Bailing out !"
    exit 1
}

source .gnuhealthrc

# Updating trytond.conf paths dynamically
sed -i -E "s|^(path *=).*|\1 $(realpath attach)|; s|^(root *=).*|\1 $(realpath gnuhealth-web)|" "$TRYTOND_CONFIG"

# Activating virtual environment
. env/bin/activate

message "INFO" "Starting GNU Health Server version ${GNUHEALTH_VERSION} ..."
cd ${GNUHEALTH_DIR}/tryton/server/${TRYTOND}/bin


python3 ./trytond $@ || bailout


