# Copyright 2019 Virantha N. Ekanayake
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions to attach sensors/motors and start the whole event loop

    #. The decorator :class:`attach` to specify peripherals that
       connect to a hub (which enables sensing and motor control functions),
    #. Initialization and shutdown functions :func:`initialize` and :func:`shutdown`.
    #. The function :func:`run` that initialize bricknil and then runs specificed "program"
       in an event loop.

"""

import logging
import pprint
from asyncio import run, sleep, get_event_loop
from asyncio import create_task as spawn
from functools import partial, wraps
import uuid

# Local imports
from .process import Process
from .ble_queue import BLEventQ
from .hub import PoweredUpHub, BoostHub, Hub

# Actual decorator that sets up the peripheral classes
# noinspection PyPep8Naming
class attach:
    """ Class-decorator to attach peripherals onto a Hub

        Injects sub-classes of `Peripheral` as instance variables on a Hub
        such as the PoweredUp Hub, akin to "attaching" a physical sensor or
        motor onto the Hub.

        Before you attach a peripheral with sensing capabilities,
        you need to ensure your `Peripheral` sub-class has the matching
        call-back method 'peripheralname_change'.

        Examples::

            @attach(PeripheralType,
                    name="instance name",
                    port='port',
                    capabilities=[])

        Warnings:
            - No support for checking to make sure user put in correct parameters
            - Identifies capabilities that need a callback update handler based purely on
              checking if the capability name starts with the string "sense*"

    """
    def __init__(self, peripheral_type, **kwargs):
        # TODO: check here to make sure parameters were entered
        if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
            print(f'decorating with {peripheral_type}')
        self.peripheral_type = peripheral_type
        self.kwargs = kwargs

    def __call__ (self, cls):
        """
            Since the actual Hub sub-class being decorated can have __init__ params,
            we need to have a wrapper function inside here to capture the arguments
            going into that __init__ call.

            Inside that wrapper, we do the following:

            # Instance the peripheral that was decorated with the saved **kwargs
            # Check that any `sense_*` capabiilities in the peripheral have an
              appropriate handler method in the hub class being decorated.
            # Instance the Hub
            # Set the peripheral instance as an instance variable on the hub via the
              `Hub.attach_sensor` method

        """
        # Define a wrapper function to capture the actual instantiation and __init__ params
        @wraps(cls)
        def wrapper_f(*args, **kwargs):
            #print(f'type of cls is {type(cls)}')
            peripheral = self.peripheral_type(**self.kwargs)
            o = cls(*args, **kwargs)
            o.message_debug(f"Decorating class {cls.__name__} with {self.peripheral_type.__name__}")
            o.attach_sensor(peripheral)
            return o
        return wrapper_f

async def initialize():
    """
    Connect and initialize all registered (instantiated) hubs
    """
    # Connect all the hubs and initialize them
    for hub in Hub.hubs:
        await hub.connect()
        await hub.initialize()



async def finalize():
    """
    Finalizes all hubs, disconnects them and cleanup everything.
    """
    for hub in Hub.hubs:
        await hub.finalize()
        await hub.disconnect()

    # Print out the port information in debug mode
    for hub in Hub.hubs:
        if hub.query_port_info:
            hub.message_info(pprint.pformat(hub.port_info))

    # At this point no device should be connected, but
    # just to make sure...
    await BLEventQ.instance.disconnect_all()

def run(program = None): #pragma: no cover
    """
    One-go helper to 
      (i)   connect and initialize all registered (instantiated) hubs, 
      (ii)  run the "program" and,
      (iii) shutdown everything.  

    Example::

    car = Car()
    async def program():
        car.speed(10)
        asyncio.sleep(10)
        car.speed(0)
    bricknil.run(program())
    """
    async def main():
        await initialize()
        try: 
            await program()
        finally:
            await finalize()
    loop = get_event_loop()
    loop.run_until_complete(main(program))



def start(setup): #pragma: no cover
    """
    Deprecated. Main entry point into running everything.

    Just pass in the async co-routine that instantiates all your hubs, and this
    function will take care of the rest.  This includes:

    Initializing the bluetooth interface object
    Starting up the user async co-routines inside the asyncio event loop

    NOTE: Using start() is deprecated, use run() instead. start() is provided
    for backward compatibility and will wanish.
    """
    import warnings
    warnings.warn("start() is deprecated, use run() instread", DeprecationWarning)


    async def main():
        await setup()
        await initialize()
        try: 
            tasks = []
            for hub in Hub.hubs:
                tasks.append(spawn(hub.run()))
            for task in tasks:
                await task
        finally:
            await finalize()
    loop = get_event_loop()
    loop.run_until_complete(main(program))