#!/usr/bin/env python3

import logging
from asyncio import sleep
from bricknil import attach, run
from bricknil.hub import CPlusHub
from bricknil.sensor.motor import CPlusXLMotor


@attach(CPlusXLMotor, name='front_drive', port=0)
@attach(CPlusXLMotor, name='rear_drive', port=1)
class XtremeOffRoader(CPlusHub):
    async def set_speed(self, speed):
        await self.front_drive.set_speed(speed)
        await self.rear_drive.set_speed(speed)


# Now, intantiate model
vehicle = XtremeOffRoader("4x4 X-treme Off Roader")

async def program():
    await vehicle.set_speed(10)
    await sleep(3)
    await vehicle.set_speed(0)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    run(program())
