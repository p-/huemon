# Copyright (c) Ely Deckers.
#
# This source code is licensed under the MPL-2.0 license found in the
# LICENSE file in the root directory of this source tree.

from hue_mon.api_interface import ApiInterface
from hue_mon.discovery_interface import Discovery


class LightsDiscovery(Discovery):
  def __init__(self, api: ApiInterface):
    self.api = api

  def name():
    return "lights"

  def exec(self, arguments=None):
    Discovery._print_array_as_discovery(self.api.get_lights()),
