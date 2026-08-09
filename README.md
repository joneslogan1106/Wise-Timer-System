# Wise Timer System
![Sketch of the timer system made with AI](images/sketch.png)
**This system requires all devices to be connected to the same internet**
## Short Repo Description
This repository serves as a timing application that allows for different peroids of time set, and wireless time changes(such as creating or removing certain peroids/quarters).

This project will be built using Flask and there will be an installation guide, below.
## Services Used
This application relies on [sockets](https://docs.python.org/3/library/socket.html) within python. It requires the sme network used for the display, the controller, and the server. 

The display uses a combination of flask and sockets in order to dynamically update according to changes from the controller.
## Code Documentation
### Server
The server serves as a simple socket server living on port 9980, which looks for the following messages:
- "INCREASE PERIOD: [peroid, time]" - This command with the arguments of the peroid number, and the amount of time (In seconds, within the client there will be an option of hours, minutes, and seconds. Server side it will be stored within seconds.) It will then increase the peroid by the amount of time.
- "DECREASE PERIOD: [peroid, time]" - This message will be sent when the controller would like to decrease the amount of time within a peroid, it would take the peroid time and subtract it from the current time stated.
- "END TIMER SERVER" - This is a command once again sent from the controller that ends everything from the server, to the display and itself being the controller.
- "REMORE PERIOD: peroid" - This shall remove a peroid from the timer
- "CREATE PERIOD: peroid" - This shall add the peroid from the timer
- "SET PERIOD TIME: [peroid, time]" - This shall allow the controller to directly edit the amount of time within a peroid for ease of use.
- "REQUEST TIMER SETTINGS" - Gives current timer settings to controller