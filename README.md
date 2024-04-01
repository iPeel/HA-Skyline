# HomeAssistant Skyline integration
This integration communicates with your Skyline hybrid inverter system, providing real-time visibility on solar output, battery status, utilisation and more. It also allows you to control the work mode and various charging / discharging parameters.

![image](https://github.com/iPeel/HA-Skyline/assets/49528212/af71b2de-1363-4bc8-8662-69e89101a9b9)

In order to use this integration, you must have connected your inverter to a Modbus to TCP/IP adapter through the RS485 port. Skyline provides no reasonable way to communicate with the inverter through the WiFi or Ethernet connections on the inverter itself, as soon as they do this integration will be updated to use it. In the meantime, a device like the Waveshare RS485 to TCP/IP adapter will work.

## Modbus adapter configuration

You will need a Modbus to TCP-RTU adapter, such as the Waveshare RS485 to Ethernet adapter: <a href="https://thepihut.com/products/rs485-to-rj45-ethernet-module">like this</a>

Once you have one, you will need to configure it by connecting to it through a web browser on 192.168.1.200, you may need to set your own computer's IP address manually to see it then log in with the password "admin".

Make sure you change the device so it has a permanent IP address on your network either with a DHCP static mapping or by assigning an IP address manually to the unit. You will then need to make the following changes:

1. Set the device port to 502
2. Set the baud rate to 9600
3. Change the protocol to Modbus TCP to RTU

<img width="1022" alt="image" src="https://github.com/iPeel/HA-Skyline/assets/49528212/b79b49ae-15fa-48fc-88ef-3cab4adfec67">

You will need to wire your inverter to the Modbus adapter, this connection is made from the RS485 port on the inverter which can be located under the cover with two ports on it. Wire up ground to any of the PE connections, then RS485 A to A and B to B. Ethernet cable works well for this, make sure you use one of the twisted pairs such as blue for the RS485 A and B connections then use any other colour for ground.

![image](https://github.com/iPeel/HA-Skyline/assets/49528212/3732f7f2-00d2-4014-8d50-6373e3b56a01)

![image](https://github.com/iPeel/HA-Skyline/assets/49528212/a35b538e-3634-4189-a244-a9d2da60e100)

If you can't find the connectors necessary on the inverter side, they can be purchased from <a href="https://cpc.farnell.com/phoenix-contact/mc-1-5-4-st-3-5/plug-free-3-5mm-4way/dp/CN18540">here</a>.

## Prerequisites

This integration is managed through the Home Assistant Community Store ( HACS ), please follow the HACS installation steps from <a href="https://hacs.xyz/">the HACS website</a> before continuing.

## Installation

From the HACS menu, press the three dots on the top right and select Custom Repositories. In the repository, enter https://github.com/iPeel/HA-Skyline and set the category to Integration. You should now be able to see the Skyline integration and choose Download from the bottom right of the Skyline integration page. If requested to do so, restart Home Assistant after downloading.

## Configuration

Once installed, add your inverter to HomeAssistant from Settings > Devices and then the Integrations tab. At the bottom right, click "Add Integration" then select "Skyline". If used for the first time, wait a minute or two while dependencies are installed. When prompted, enter the IP address of your Modbus adapter. The integration then scans for Modbus slaves, adding all inverters discovered.

### Multiple parallel inverters

If you have multiple inverters they can either be connected to the same modbus adapter, with each inverter configured with a unique slave address in the Communications settings in the Solar Touch App or by using multiple Modbus adapters. Currently Skyline incorrectly synchronises the modbus address of each host when inverters are connected in parallel, and are yet to fix this issue ( if ever ). This means for parallel mode inverters you need multiple Modbus adapters.

To use multiple modbus adapters, in the integration configuration provide each IP address separated by commas. At startup the integration scans for inverters and will present each inverter in a parallel configuration as a separate inverter.

Note when inverters are in parallel, inverters will report their respective power settings adjusted for the number of inverters and will share and setting equally between them. For example, with 2 parallel inverters the Grid Charge Max Power setting will read 6kW from each inverter but present this as 12kW in Home Assistant, then any change of setting will halve the set amount for each inverter, so setting to 10kW will end up as 5kW on each inverter.

When more than one inverter is discovered, some additional entities are registered which provide summed power for solar output, inverter output and grid / house / EPS demand. These are integration entities and not linked to any specific device so are only visible under the main integration entities view.

## Feed In Excess Solar mode

There is a "Match Feed In To Excess Solar" setting which attempts to overcome issues with parallel inverters where inverters de-rate solar when the battery is full or restricted to a specific charge rate or SoC, making it difficult to export excess solar. When enabled and the inverter is in "Feed In Priority" mode, each 10 minute period the Max Feed In Power setting is tweaked based on the average of excess solar over the previous 10 minutes. Excess solar is calculated based on the average PV power minus the average consumption ( EPS + grid tied loads ). The amount of feed in is compensated to attempt to keep the battery SoC around a setpoint, with feed in power increased or decreased based on a parameter per 10% SoC difference. This mode can also always feed in some power by a specified amount even when there is no excess, so that there will always be a little "push" on the grid to overcome the inverter's inherent lack of dynamic power control.

The parameters controlling this mode can be set by configuring the integration, there is a value to determine the target SoC percentage to balance around, the amount to increase or decrease solar by to maintain the setpoint, and the amount of minimum feed in power when no excess is available. You can also set these parameters in runtime by calling the "cyg_skyline.set_excess_params" service with a payload containing any parameters you want to change ( it's not necessary to include keys you do not want to change ):

![image](https://github.com/iPeel/HA-Skyline/assets/49528212/27cbc741-ab14-4062-8eed-12999443dbf3)

There is an entity "Skyline Excess PV Power" which provides the current calculation of excess over the last 10 minutes, note this entity can be negative if PV is less than demand, and this value does not display any adjustments for SoC balancing.

## Current Limitations

Polling intervals are fixed at 10 seconds since the previous poll, this seems "real-time" enough.

The integration currently assumes the inverter model is a 6kW type, the intention in future releases is to limit max charge / discharge parameters based on inverter model however for the moment you will need to configure only for the max rating of your inverter otherwise commands will probably fail.

There are no battery temperature sensors, as Skyline do not currently write the battery temperature address correctly ( it's always zero ). This has been reported but as yet Skyline have not acknowledged the problem and as a result this sensor is not published.

In the event of a communication failure, the integration will retry writes if sensor readings do not match a recent set request. There are 9 retry attempts and this is to ensure that any communications issues with the inverter are recovered. If you make a setting which your inverter does not support then the integration may keep retrying the setting when data read does not match what data was written.

Many sensors are in English only and have no International translations, this is a work in progress.

Sometimes sensors will read zero, this is an issue with Skyline reporting and not the integration, you may have noticed this already in the Solar Touch app or on the cloudinverter web view. It seems that sometimes the inverter reports zero values. Solar output and grid utilisation seem to be the worse for this and as a reult the integration averages readings over the past 30 seconds. Also bear in mind that statistics are gathered from multiple requests and therefore due to the dynamic nature of the inverter some statistics may not add up as they are gathered at very slightly different points in time, this is expecially true for parallel inverters, where some individual values ( like grid power ) are broken up and distributed across multiple inverters and may change dynamically during the duration of a poll.

If you shut down the inverter then at startup the inverter may report zero values for all historic readings, the integration makes an attempt to spot this and not post the data to HA but for the sake of historic sensor readings it is recommended to turn off the Modbus adapter when restarting the inverter.
