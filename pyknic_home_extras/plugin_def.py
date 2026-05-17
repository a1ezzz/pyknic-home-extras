# -*- coding: utf-8 -*-
# pyknic_home_extras/plugin_def.py
#
# Copyright (C) 2026 the pyknic-home-extras authors and contributors
# <see AUTHORS file>
#
# This file is part of pyknic-home-extras.
#
# pyknic-home-extras is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyknic-home-extras is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with pyknic-home-extras.  If not, see <http://www.gnu.org/licenses/>.

# TODO: document the code
# TODO: write tests for the code

from pyknic.lib.bellboy.app import register_bellboy_command

from pyknic_home_extras.photo_sorter import BellBoyPhotoSorterCommand


def init_plugin() -> None:
    register_bellboy_command()(BellBoyPhotoSorterCommand)
