# -*- coding: utf-8 -*-
# pyknic_home_extras/photo_sorter.py
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
import contextlib

# TODO: document the code
# TODO: write tests for the code

import datetime
import filecmp
import json
import os
import shutil
import subprocess
import typing

import magic
import pydantic

from pyknic.lib.log import Logger
from pyknic.lib.io.aio_wrapper import AsyncWrapper
from pyknic.lib.bellboy.app import BellBoyCommandHandler
from pyknic.lib.fastapi.models.lobby import LobbyCommandResult, LobbyKeyValueFeedbackResult


class PhotoSorterCommandModel(pydantic.BaseModel):

    input: typing.List[str] = pydantic.Field(description='source files/directories to sort')

    output: str = pydantic.Field(description='destination directory')


class BellBoyPhotoSorterCommand(BellBoyCommandHandler):

    def __init__(self, args: pydantic.BaseModel):
        BellBoyCommandHandler.__init__(self, args)
        self.__magic = magic.open(magic.MIME_TYPE)  # type: ignore[attr-defined]  # external lib
        self.__magic.load()

    @classmethod
    def command_name(cls) -> str:
        """ The :meth:`.BellBoyCommandHandler.command_name` method implementation
        """
        return 'photo-sorter'

    @classmethod
    def command_model(cls) -> typing.Type[pydantic.BaseModel]:
        """ The :meth:`.BellBoyCommandHandler.command_model` method implementation
        """
        return PhotoSorterCommandModel

    async def exec(self) -> LobbyCommandResult:
        caller = await AsyncWrapper.create(self.__sort)
        return await caller()  # type: ignore[no-any-return]

    def __check_exiftool(self) -> None:

        cmd_result = None

        with contextlib.suppress(FileNotFoundError):
            cmd_result = subprocess.run(["exiftool", "-echo", "test"])

        if cmd_result is None or cmd_result.returncode:
            raise ValueError('The "exiftool" command was not found or corrupted!')

    def __files_generator(self) -> typing.Generator[str, None, None]:
        assert(isinstance(self._args, PhotoSorterCommandModel))

        def on_error(e: Exception) -> None:
            raise e

        for input_entry in self._args.input:

            if os.path.isfile(input_entry):
                yield input_entry
            elif os.path.isdir(input_entry):

                for search_dir, inner_dirs, inner_files in os.walk(input_entry, onerror=on_error):
                    for i in inner_files:
                        yield str(os.path.join(search_dir, i))
            else:
                Logger.error(f'Non regular file or directory spotted -- "{input_entry}" (skipping)')

    def __mime_type(self, file_path: str) -> str:
        return self.__magic.file(file_path)  # type: ignore[no-any-return]  # external lib

    def __get_exif(self, file_path: str) -> dict[str, typing.Any]:
        tags_cmd = subprocess.run(
            ["exiftool", "-json", "-d", '%Y:%m:%d %H:%M:%S', file_path], check=True, capture_output=True
        )
        str_tags = tags_cmd.stdout.decode()
        return json.loads(str_tags)[0]  # type: ignore[no-any-return]  # external app

    def __file_destination(self, file_path: str) -> typing.Optional[str]:
        assert(isinstance(self._args, PhotoSorterCommandModel))

        Logger.info(f'The file "{file_path}". MIME type is: {self.__mime_type(file_path)}')

        exif_info = self.__get_exif(file_path)
        exif_date = exif_info.get('DateTimeOriginal')

        Logger.info(f'The file "{file_path}". EXIF date is: {exif_date}')

        if exif_date and exif_date != '0000:00:00 00:00:00':
            parsed_date = datetime.datetime.strptime(exif_date, '%Y:%m:%d %H:%M:%S')
            base_path = parsed_date.strftime(f'%Y{os.sep}%m-%B{os.sep}%d_%B_%Y_%H-%M-%S')
        else:
            base_path = f'Unknown{os.sep}photo'

        file_extension = os.path.splitext(file_path)[1]

        result = f'{self._args.output}{os.sep}{base_path}{file_extension}'
        file_suffix = None

        while True:
            if not os.path.exists(result):
                return result

            if filecmp.cmp(file_path, result, shallow=False):
                Logger.warning(f'Duplicated files spotted: {file_path} and {result}, so skip the "{file_path}"')
                return None

            if file_suffix is None:
                file_suffix = 2
            else:
                file_suffix += 1

            result = f'{self._args.output}{os.sep}{base_path}_{file_suffix}{file_extension}'

    def __sort(self) -> LobbyCommandResult:
        assert(isinstance(self._args, PhotoSorterCommandModel))

        self.__check_exiftool()

        if not os.path.isdir(self._args.output):
            raise ValueError(f'There is no such directory "{self._args.output}"')

        files_processed = 0
        files_copied = 0
        files_skipped = 0

        for file_path in self.__files_generator():

            files_processed += 1

            if self.__mime_type(file_path).startswith('image/'):
                destination_file = self.__file_destination(file_path)
                if destination_file is not None:

                    destination_dir = os.path.dirname(destination_file)
                    if not os.path.exists(destination_dir):
                        os.makedirs(destination_dir)

                    shutil.copyfile(file_path, destination_file)
                    Logger.info(f'The "{file_path}" file has been copied to "{destination_file}"')
                    files_copied += 1
                    continue

                else:
                    Logger.info(f'The "{file_path}" file has been skipped because of duplicate')

            else:
                Logger.info(f'Skipping non-image file -- "{file_path}"')

            files_skipped += 1

        return LobbyKeyValueFeedbackResult(
            kv_result={
                'files_processed': files_processed,
                'files_copied': files_copied,
                'files_skipped': files_skipped
            }
        )
