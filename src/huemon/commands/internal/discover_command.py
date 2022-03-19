# Copyright (c) Ely Deckers.
#
# This source code is licensed under the MPL-2.0 license found in the
# LICENSE file in the root directory of this source tree.

import os
from functools import reduce
from typing import Dict, List, Type, TypeVar

from huemon.api.api_interface import ApiInterface
from huemon.commands.hue_command_interface import HueCommand
from huemon.discoveries.discovery_interface import Discovery
from huemon.infrastructure.logger_factory import create_logger
from huemon.infrastructure.plugin_loader import load_plugins
from huemon.sinks.sink_interface import SinkInterface
from huemon.utils.assertions import assert_exists_e, assert_num_args_e
from huemon.utils.common import fst
from huemon.utils.monads.either import Either, rights
from huemon.utils.monads.maybe import Maybe, maybe, of
from huemon.utils.paths import create_local_path
from huemon.utils.plugins import get_discovery_plugins_path

LOG = create_logger()

TA = TypeVar("TA")
TB = TypeVar("TB")


def create_discovery_handlers(
    api: ApiInterface, sink: SinkInterface, plugins: List[Type[Discovery]]
) -> Dict[str, Discovery]:
    return reduce(lambda p, c: {**p, c.name(): c(api, sink)}, plugins, {})


class DiscoveryHandler:  # pylint: disable=too-few-public-methods
    def __init__(self, handlers):
        self.handlers = handlers

    def exec(self, discovery_type):
        LOG.debug(
            "Running `%s` command (discovery_type=%s)",
            DiscoverCommand.name(),
            discovery_type,
        )
        target, maybe_sub_target, *_ = discovery_type.split(":") + [None]

        assert_exists_e(list(self.handlers), target).fmap(
            lambda tx: self.handlers[tx]
        ).fmap(lambda hlr: hlr.exec([maybe_sub_target] if maybe_sub_target else []))

        LOG.debug(
            "Finished `%s` command (discovery_type=%s)",
            DiscoverCommand.name(),
            discovery_type,
        )


class Discover:  # pylint: disable=too-few-public-methods
    def __init__(self, config: dict, api: ApiInterface, sink: SinkInterface):
        self.discovery_plugins_path = get_discovery_plugins_path(config)

        self.handler = self.__create_discovery_handler(api, sink)

    def __create_discovery_handler(self, api: ApiInterface, sink: SinkInterface):
        LOG.debug("Loading discovery plugins (path=%s)", self.discovery_plugins_path)
        discovery_handler_plugins = create_discovery_handlers(
            api,
            sink,
            rights(
                Discover.__load_plugins_and_hardwired_handlers(
                    of(self.discovery_plugins_path)
                )
            ),
        )
        LOG.debug(
            "Finished loading discovery plugins (path=%s)", self.discovery_plugins_path
        )

        return DiscoveryHandler(discovery_handler_plugins)

    @staticmethod
    def __load_discovery_plugin(path: str):
        return load_plugins("discovery", path, Discovery)

    @staticmethod
    def __load_plugins_and_hardwired_handlers(
        discovery_plugins_path: Maybe[str],
    ) -> List[Either[str, Type[Discovery]]]:
        hardwired_discoveries_path = create_local_path(
            os.path.join("discoveries", "internal")
        )

        return maybe(
            [], Discover.__load_discovery_plugin, discovery_plugins_path
        ) + Discover.__load_discovery_plugin(hardwired_discoveries_path)

    def discover(self, discovery_type):
        self.handler.exec(discovery_type)


class DiscoverCommand(HueCommand):
    def __init__(self, config: dict, api: ApiInterface, processor: SinkInterface):
        super().__init__(config, api, processor)

        self.discovery = Discover(config, api, processor)

    @staticmethod
    def name():
        return "discover"

    def exec(self, arguments: List[str]):
        LOG.debug(
            "Running `%s` command (arguments=%s)", DiscoverCommand.name(), arguments
        )

        error, param = assert_num_args_e(1, arguments, DiscoverCommand.name()).fmap(
            fst  # type: ignore
        )

        if error:
            self.processor.process(error)
            return

        self.discovery.discover(param)

        LOG.debug(
            "Finished `%s` command (arguments=%s)", DiscoverCommand.name(), arguments
        )
